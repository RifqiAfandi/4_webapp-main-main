# counter/views.py
import os
import shutil
import json
import traceback

from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required 
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.files.storage import default_storage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .forms import LoginForm

from .models import DetectionResult, BoundingBox, BobotResult, BobotDetection
from .yolo_model import detect_semangka
from .bobot_model import estimate_bobot

# from django.contrib.auth.forms import UserCreationForm
from .forms import LoginForm, CustomSignupForm
from django.contrib.auth import logout

# counter/views.py (Bagian login_view saja)

def login_view(request):
    if request.user.is_authenticated:
        return redirect("counter:home")
        
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            # UBAH: Ambil 'email', bukan 'username'
            email = form.cleaned_data["email"] 
            password = form.cleaned_data["password"]
            
            # UBAH: Kirim argumen email ke fungsi authenticate
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, "Selamat datang kembali!")
                return redirect("counter:home")
            else:
                messages.error(request, "Email atau password salah.")
    else:
        form = LoginForm()
    
    return render(request, "accounts/login.html", {"form": form})
    
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("counter:home")

    if request.method == "POST":
        # UBAH: Gunakan CustomSignupForm di sini
        form = CustomSignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            
            # Menambahkan parameter backend secara eksplisit agar Django tidak bingung
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            messages.success(request, "Akun berhasil dibuat!")
            return redirect("counter:home")
        else:
            messages.error(request, "Terjadi kesalahan pada pendaftaran.")
    else:
        # UBAH: Gunakan CustomSignupForm di sini juga
        form = CustomSignupForm()
    
    return render(request, "accounts/signup.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "Anda telah keluar.")
    
    return redirect("/accounts/login/")

def _fs_path_to_media_url(fs_path: str) -> str:
    """
    Ubah absolute filesystem path (MEDIA_ROOT/...) ke URL (/media/...)
    """
    fs_path = os.path.abspath(fs_path)
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    rel_path = os.path.relpath(fs_path, media_root)
    rel_path = rel_path.replace("\\", "/")
    return settings.MEDIA_URL.rstrip("/") + "/" + rel_path.lstrip("/")


def _effective_count(result: DetectionResult) -> int:
    """
    Hitung jumlah semangka yang dipakai tampilan:
    - kalau manual_count > 0 pakai itu (hasil edit),
    - kalau belum pernah edit pakai count (hasil YOLO).
    """
    return result.manual_count if result.manual_count and result.manual_count > 0 else result.count


@login_required(login_url="/accounts/login/")
def home(request):
    if request.method == "POST":
        lahan = request.POST.get("lahan")
        image = request.FILES.get("image")

        print(f"🎯 UPLOAD: {lahan}, {image}")

        if not lahan or not image:
            messages.error(request, "⚠️ Lengkapi lahan dan file orthophoto.")
            return redirect("counter:home")

        try:
            # simpan file asli
            filename = default_storage.save(f"orthophoto/{image.name}", image)
            original_path = default_storage.path(filename)
            print(f"✅ ASLI TERSIMPAN: {original_path}")

            # jalankan YOLO -> HARUS return (count, out_path, bboxes, extra)
            count, bbox_fs_path, bboxes, _ = detect_semangka(original_path)
            print(f"✅ YOLO OK: {count} semangka, hasil di {bbox_fs_path}")

            # konversi ke URL
            image_url = _fs_path_to_media_url(default_storage.path(filename))
            bbox_url = _fs_path_to_media_url(bbox_fs_path)

            # simpan DetectionResult
            result = DetectionResult.objects.create(
                user=request.user,
                filename=image.name,
                lahan=lahan,
                image_path=image_url,
                bbox_path=bbox_url,
                count=count,          # hasil YOLO
                manual_count=count,   # awalnya sama
            )

            # simpan semua bbox awal ke tabel BoundingBox
            for (x1, y1, x2, y2) in bboxes:
                BoundingBox.objects.create(
                    result=result,
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )

            messages.success(
                request, f"✅ Upload berhasil! {count} semangka terdeteksi."
            )

        except Exception as e:
            print(f"❌ ERROR upload/deteksi: {e}")
            traceback.print_exc()
            messages.error(request, f"❌ Error: {e}")
            return redirect("counter:home")

        return redirect("counter:home")

    # GET: tampilkan dashboard
    all_results = DetectionResult.objects.filter(user=request.user).order_by("-created_at")
    latest = all_results[:1]
    history = all_results[1:]

    context = {
        "total_ortho": all_results.count(),
        "total_detected": sum(_effective_count(r) for r in all_results),
        "latest": latest,
        "history": history,
        "page_title": "Dashboard Utama",
        "all_results_list": all_results,
    }
    return render(request, "counter/home.html", context)


@login_required(login_url="/accounts/login/")
def detail_orthophoto(request, pk):
    try:
        result = DetectionResult.objects.get(pk=pk, user=request.user)
    except DetectionResult.DoesNotExist:
        raise Http404("Result not found")

    boxes = list(result.boxes.all())  # related_name='boxes'

    context = {
        "result": result,
        "boxes": boxes,
        "page_title": f"Detail Orthophoto - {result.filename}",
    }
    return render(request, "counter/detail_orthophoto.html", context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url="/accounts/login/")
def save_boxes(request, pk):
    try:
        result = DetectionResult.objects.get(pk=pk, user=request.user)
    except DetectionResult.DoesNotExist:
        return JsonResponse({"error": "Result not found"}, status=404)

    try:
        data = json.loads(request.body)
        boxes = data.get("boxes", [])

        # hapus semua bbox lama
        BoundingBox.objects.filter(result=result).delete()

        # simpan semua bbox terbaru
        for b in boxes:
            BoundingBox.objects.create(
                result=result,
                x1=b.get("x1", 0),
                y1=b.get("y1", 0),
                x2=b.get("x2", 0),
                y2=b.get("y2", 0),
            )

        # manual_count = jumlah bbox sekarang
        result.manual_count = len(boxes)
        result.save()

        return JsonResponse({"count": result.manual_count})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required(login_url="/accounts/login/")
def history(request):
    all_results = DetectionResult.objects.filter(user=request.user).order_by("-created_at")
    latest = all_results[:1]
    history_qs = all_results[1:]

    all_bobot = BobotResult.objects.filter(user=request.user).order_by("-created_at")

    context = {
        "total_ortho": all_results.count(),
        "total_detected": sum(_effective_count(r) for r in all_results),
        "latest": latest,
        "history": history_qs,
        "total_ortho_bobot": all_bobot.count(),
        "total_deteksi_bobot": sum(r.total_terdeteksi for r in all_bobot),
        "history_bobot": all_bobot,
        "page_title": "History",
    }
    return render(request, "counter/history.html", context)


@require_POST
@login_required(login_url="/accounts/login/")
def delete_result(request, pk):
    """
    Hapus 1 DetectionResult + file gambarnya (image & bbox).
    Dipanggil via fetch dari tombol 'Hapus' di history.
    """
    try:
        result = DetectionResult.objects.get(pk=pk, user=request.user)
    except DetectionResult.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found"}, status=404)

    # hapus file fisik
    def remove_file(url_path):
        if not url_path:
            return
        rel = url_path.replace(settings.MEDIA_URL, "").lstrip("/")
        fs_path = os.path.join(settings.MEDIA_ROOT, rel)
        if os.path.exists(fs_path):
            os.remove(fs_path)

    remove_file(result.image_path)
    remove_file(result.bbox_path)

    # hapus bbox terkait
    BoundingBox.objects.filter(result=result).delete()
    result.delete()
    return JsonResponse({"ok": True})


def _hitung_dominan(rekap: dict):
    """Cari kelas dengan jumlah deteksi terbanyak dari hasil rekap estimate_bobot."""
    if not rekap:
        return None, None, 0
    kelas_terpilih = max(rekap.items(), key=lambda item: item[1]["jumlah"])
    kelas, info = kelas_terpilih
    return kelas, info["range_bobot"], info["jumlah"]


@login_required(login_url="/accounts/login/")
def hitung_bobot(request):
    if request.method == "POST":
        lahan = request.POST.get("lahan")
        image = request.FILES.get("image")

        if not lahan or not image:
            messages.error(request, "⚠️ Lengkapi lahan dan file orthophoto.")
            return redirect("counter:hitung_bobot")

        try:
            filename = default_storage.save(f"orthophoto/{image.name}", image)
            original_path = default_storage.path(filename)

            rekap, bbox_fs_path, detections = estimate_bobot(original_path)

            image_url = _fs_path_to_media_url(default_storage.path(filename))
            bbox_url = _fs_path_to_media_url(bbox_fs_path)

            kelas_dominan, range_dominan, jumlah_dominan = _hitung_dominan(rekap)
            total_terdeteksi = sum(info["jumlah"] for info in rekap.values())

            result = BobotResult.objects.create(
                user=request.user,
                filename=image.name,
                lahan=lahan,
                image_path=image_url,
                bbox_path=bbox_url,
                total_terdeteksi=total_terdeteksi,
                kelas_dominan=kelas_dominan or "",
                range_dominan=range_dominan or "",
                jumlah_dominan=jumlah_dominan,
            )

            for d in detections:
                x1, y1, x2, y2 = d["bbox"]
                BobotDetection.objects.create(
                    result=result,
                    kelas=d["kelas"],
                    range_bobot=d["range_bobot"],
                    warna_marker=d["warna_marker"],
                    confidence=d["conf"],
                    x1=x1, y1=y1, x2=x2, y2=y2,
                )

            messages.success(
                request,
                f"✅ Upload berhasil! {total_terdeteksi} semangka terdeteksi, "
                f"kategori dominan: {range_dominan or '-'}."
            )

        except Exception as e:
            print(f"❌ ERROR hitung_bobot: {e}")
            traceback.print_exc()
            messages.error(request, f"❌ Error: {e}")
            return redirect("counter:hitung_bobot")

        return redirect("counter:hitung_bobot")

    # GET
    all_bobot = BobotResult.objects.filter(user=request.user).order_by("-created_at")
    latest_bobot = all_bobot[:1]
    history_bobot = all_bobot[1:]

    all_semangka = DetectionResult.objects.filter(user=request.user).order_by("-created_at")
    latest_semangka = all_semangka[:1]
    history_semangka = all_semangka[1:]

    context = {
        "total_ortho": all_semangka.count(),
        "total_detected": sum(_effective_count(r) for r in all_semangka),
        "latest": latest_semangka,
        "history": history_semangka,
        "total_ortho_bobot": all_bobot.count(),
        "total_deteksi_bobot": sum(r.total_terdeteksi for r in all_bobot),
        "latest_bobot": latest_bobot,
        "history_bobot": history_bobot,
        "page_title": "Dashboard Utama",
        "all_results_list": all_semangka,
        "all_bobot_list": all_bobot,
    }
    return render(request, "counter/home.html", context)


@require_POST
@login_required(login_url="/accounts/login/")
def delete_bobot_result(request, pk):
    """
    Hapus 1 BobotResult + file gambarnya (image & bbox).
    Dipanggil via fetch dari tombol 'Hapus' di Live Analisis Bobot.
    """
    try:
        result = BobotResult.objects.get(pk=pk, user=request.user)
    except BobotResult.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Not found"}, status=404)

    # hapus file fisik
    def remove_file(url_path):
        if not url_path:
            return
        rel = url_path.replace(settings.MEDIA_URL, "").lstrip("/")
        fs_path = os.path.join(settings.MEDIA_ROOT, rel)
        if os.path.exists(fs_path):
            os.remove(fs_path)

    remove_file(result.bbox_path)
    # image_path (file asli) tidak dihapus karena bisa dipakai ulang

    # hapus detections terkait
    BobotDetection.objects.filter(result=result).delete()
    result.delete()
    return JsonResponse({"ok": True})

