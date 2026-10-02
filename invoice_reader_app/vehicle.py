from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from invoice_reader_app.models_vehicle import Vehicle


def update_vehicle_from_post(vehicle, request):

    # -----------------------------------------------------
    # NHẬN DẠNG
    # -----------------------------------------------------

    vehicle.license_plate = request.POST.get(
        "license_plate", ""
    ).strip()

    vehicle.vehicle_record_no = request.POST.get(
        "vehicle_record_no", ""
    ).strip()

    vehicle.vehicle_type = request.POST.get(
        "vehicle_type", ""
    ).strip()

    vehicle.brand = request.POST.get(
        "brand", ""
    ).strip()

    vehicle.model = request.POST.get(
        "model", ""
    ).strip()

    vehicle.color = request.POST.get(
        "color", ""
    ).strip()

    vehicle.chassis_number = request.POST.get(
        "chassis_number", ""
    ).strip()

    vehicle.engine_number = request.POST.get(
        "engine_number", ""
    ).strip()

    vehicle.engine_model = request.POST.get(
        "engine_model", ""
    ).strip()

    # -----------------------------------------------------
    # SẢN XUẤT
    # -----------------------------------------------------

    vehicle.manufacture_year = (
        request.POST.get("manufacture_year") or None
    )

    vehicle.production_country = request.POST.get(
        "production_country", ""
    ).strip()

    vehicle.lifetime_limit = (
        request.POST.get("lifetime_limit") or None
    )

    vehicle.commercial_use = (
        request.POST.get("commercial_use") == "on"
    )

    vehicle.modified_vehicle = (
        request.POST.get("modified_vehicle") == "on"
    )

    # -----------------------------------------------------
    # KÍCH THƯỚC
    # -----------------------------------------------------

    vehicle.overall_dimensions = request.POST.get(
        "overall_dimensions", ""
    ).strip()

    vehicle.wheelbase = request.POST.get(
        "wheelbase", ""
    ).strip()

    vehicle.cargo_dimensions = request.POST.get(
        "cargo_dimensions", ""
    ).strip()

    # -----------------------------------------------------
    # KHỐI LƯỢNG
    # -----------------------------------------------------

    vehicle.curb_weight = (
        request.POST.get("curb_weight") or None
    )

    vehicle.total_weight_design = (
        request.POST.get("total_weight_design") or None
    )

    vehicle.total_weight_authorized = (
        request.POST.get("total_weight_authorized") or None
    )

    vehicle.load_capacity_design = (
        request.POST.get("load_capacity_design") or None
    )

    vehicle.load_capacity_authorized = (
        request.POST.get("load_capacity_authorized") or None
    )

    vehicle.towing_capacity_design = (
        request.POST.get("towing_capacity_design") or None
    )

    vehicle.towing_capacity_authorized = (
        request.POST.get("towing_capacity_authorized") or None
    )

    # Trường tương thích cũ
    vehicle.load_capacity = (
        request.POST.get("load_capacity") or
        request.POST.get("load_capacity_authorized") or
        None
    )

    vehicle.total_weight = (
        request.POST.get("total_weight") or
        request.POST.get("total_weight_authorized") or
        None
    )

    # -----------------------------------------------------
    # HÀNH KHÁCH
    # -----------------------------------------------------

    vehicle.passenger_capacity = (
        request.POST.get("passenger_capacity") or None
    )

    vehicle.standing_capacity = (
        request.POST.get("standing_capacity") or None
    )

    vehicle.lying_capacity = (
        request.POST.get("lying_capacity") or None
    )

    vehicle.wheelchair_capacity = (
        request.POST.get("wheelchair_capacity") or None
    )

    # -----------------------------------------------------
    # BÁNH XE
    # -----------------------------------------------------

    vehicle.drive_configuration = request.POST.get(
        "drive_configuration", ""
    ).strip()

    vehicle.tire_tread = request.POST.get(
        "tire_tread", ""
    ).strip()

    vehicle.tire_specification = request.POST.get(
        "tire_specification", ""
    ).strip()

    # -----------------------------------------------------
    # ĐỘNG CƠ
    # -----------------------------------------------------

    vehicle.engine_type = request.POST.get(
        "engine_type", ""
    ).strip()

    vehicle.engine_displacement = (
        request.POST.get("engine_displacement") or None
    )

    vehicle.fuel_type = request.POST.get(
        "fuel_type", ""
    ).strip()

    vehicle.emission_level = request.POST.get(
        "emission_level", ""
    ).strip()

    vehicle.max_power = (
        request.POST.get("max_power") or None
    )

    vehicle.max_power_rpm = (
        request.POST.get("max_power_rpm") or None
    )

    # -----------------------------------------------------
    # THIẾT BỊ
    # -----------------------------------------------------

    vehicle.has_tachograph = (
        request.POST.get("has_tachograph") == "on"
    )

    vehicle.has_passenger_camera = (
        request.POST.get("has_passenger_camera") == "on"
    )

    vehicle.has_driver_camera = (
        request.POST.get("has_driver_camera") == "on"
    )

    vehicle.has_child_detection = (
        request.POST.get("has_child_detection") == "on"
    )

    vehicle.carries_explosives = (
        request.POST.get("carries_explosives") == "on"
    )

    # -----------------------------------------------------
    # ĐĂNG KIỂM
    # -----------------------------------------------------

    vehicle.inspection_number = request.POST.get(
        "inspection_number", ""
    ).strip()

    vehicle.inspection_date = (
        request.POST.get("inspection_date") or None
    )

    vehicle.inspection_expiry = (
        request.POST.get("inspection_expiry") or None
    )

    vehicle.inspection_sticker_number = request.POST.get(
        "inspection_sticker_number", ""
    ).strip()

    vehicle.inspection_stamp_issued = (
        request.POST.get("inspection_stamp_issued") == "on"
    )

    vehicle.exempt_initial_inspection = (
        request.POST.get("exempt_initial_inspection") == "on"
    )

    vehicle.inspection_station = request.POST.get(
        "inspection_station", ""
    ).strip()

    vehicle.inspection_signer = request.POST.get(
        "inspection_signer", ""
    ).strip()

    vehicle.inspection_verification_url = request.POST.get(
        "inspection_verification_url", ""
    ).strip()

    vehicle.inspection_qr_code = request.POST.get(
        "inspection_qr_code", ""
    ).strip()

    # -----------------------------------------------------
    # PHÙ HIỆU
    # -----------------------------------------------------

    vehicle.badge_number = request.POST.get(
        "badge_number", ""
    ).strip()

    vehicle.badge_expiry = (
        request.POST.get("badge_expiry") or None
    )

    # -----------------------------------------------------
    # QUẢN LÝ
    # -----------------------------------------------------

    vehicle.put_into_use_date = (
        request.POST.get("put_into_use_date") or None
    )

    vehicle.status = request.POST.get(
        "status",
        "active"
    )

    vehicle.notes = request.POST.get(
        "notes", ""
    ).strip()

    return vehicle


def vehicle_list(request):

    vehicles = Vehicle.objects.all().order_by(
        "license_plate"
    )

    today = date.today()
    warning_date = today + timedelta(days=30)

    for vehicle in vehicles:

        # Đăng kiểm
        if not vehicle.inspection_expiry:
            vehicle.inspection_status = "unknown"
            vehicle.inspection_status_text = "Chưa có"

        elif vehicle.inspection_expiry < today:
            vehicle.inspection_status = "expired"
            vehicle.inspection_status_text = "Đã hết hạn"

        elif vehicle.inspection_expiry <= warning_date:
            vehicle.inspection_status = "warning"
            vehicle.inspection_status_text = "Sắp hết hạn"

        else:
            vehicle.inspection_status = "valid"
            vehicle.inspection_status_text = "Còn hạn"

        # Phù hiệu
        if not vehicle.badge_expiry:
            vehicle.badge_status = "unknown"
            vehicle.badge_status_text = "Chưa có"

        elif vehicle.badge_expiry < today:
            vehicle.badge_status = "expired"
            vehicle.badge_status_text = "Đã hết hạn"

        elif vehicle.badge_expiry <= warning_date:
            vehicle.badge_status = "warning"
            vehicle.badge_status_text = "Sắp hết hạn"

        else:
            vehicle.badge_status = "valid"
            vehicle.badge_status_text = "Còn hạn"

    return render(
        request,
        "vehicles/vehicle_list.html",
        {
            "vehicles": vehicles,
            "today": today,
        }
    )


@login_required
def vehicle_create(request):

    if request.method == "POST":

        license_plate = request.POST.get(
            "license_plate",
            ""
        ).strip()

        if not license_plate:

            messages.error(
                request,
                "Vui lòng nhập biển số xe."
            )

            return render(
                request,
                "vehicles/vehicle_form.html"
            )

        if Vehicle.objects.filter(
            license_plate__iexact=license_plate
        ).exists():

            messages.error(
                request,
                "Biển số xe đã tồn tại."
            )

            return render(
                request,
                "vehicles/vehicle_form.html"
            )

        vehicle = Vehicle()

        update_vehicle_from_post(
            vehicle,
            request
        )

        vehicle.save()

        messages.success(
            request,
            f"Đã thêm phương tiện {vehicle.license_plate}."
        )

        return redirect("vehicles")

    return render(
        request,
        "vehicles/vehicle_form.html"
    )


@login_required
def vehicle_edit(request, pk):

    vehicle = get_object_or_404(
        Vehicle,
        pk=pk
    )

    if request.method == "POST":

        license_plate = request.POST.get(
            "license_plate",
            ""
        ).strip()

        if not license_plate:

            messages.error(
                request,
                "Vui lòng nhập biển số xe."
            )

            return render(
                request,
                "vehicles/vehicle_form.html",
                {"vehicle": vehicle}
            )

        if Vehicle.objects.filter(
            license_plate__iexact=license_plate
        ).exclude(
            pk=vehicle.pk
        ).exists():

            messages.error(
                request,
                "Biển số xe đã được sử dụng."
            )

            return render(
                request,
                "vehicles/vehicle_form.html",
                {"vehicle": vehicle}
            )

        update_vehicle_from_post(
            vehicle,
            request
        )

        vehicle.save()

        messages.success(
            request,
            f"Đã cập nhật phương tiện {vehicle.license_plate}."
        )

        return redirect("vehicles")

    return render(
        request,
        "vehicles/vehicle_form.html",
        {
            "vehicle": vehicle
        }
    )

@login_required
def vehicle_delete(request, pk):

    vehicle = get_object_or_404(
        Vehicle,
        pk=pk
    )

    if request.method == "POST":

        license_plate = vehicle.license_plate

        vehicle.delete()

        messages.success(
            request,
            f"Đã xóa phương tiện {license_plate}."
        )

        return redirect("vehicles")

    return render(
        request,
        "vehicles/vehicle_confirm_delete.html",
        {
            "vehicle": vehicle
        }
    )