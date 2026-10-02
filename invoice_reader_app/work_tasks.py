from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator


from .models_worktask import WorkTask

@login_required
def work_task_list(request):

    keyword = request.GET.get(
        "q",
        ""
    ).strip()

    tasks = (
        WorkTask.objects
        .select_related("handler")
        .all()
    )

    # =====================================================
    # TÌM KIẾM
    # =====================================================

    if keyword:
        tasks = tasks.filter(
            Q(content__icontains=keyword)
            | Q(handler__username__icontains=keyword)
            | Q(handler__first_name__icontains=keyword)
            | Q(handler__last_name__icontains=keyword)
            | Q(process_content__icontains=keyword)
        )

    # =====================================================
    # SẮP XẾP
    # =====================================================

    tasks = tasks.annotate(
        status_order=Case(
            When(
                status=WorkTask.STATUS_PENDING,
                then=Value(0)
            ),
            When(
                status=WorkTask.STATUS_COMPLETED,
                then=Value(1)
            ),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by(
        "status_order",
        "-work_date",
        "-id",
    )

    # =====================================================
    # PHÂN TRANG
    # =====================================================

    paginator = Paginator(
        tasks,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # =====================================================
    # THỐNG KÊ
    # =====================================================

    total_tasks = WorkTask.objects.count()

    pending_tasks = WorkTask.objects.filter(
        status=WorkTask.STATUS_PENDING
    ).count()

    completed_tasks = WorkTask.objects.filter(
        status=WorkTask.STATUS_COMPLETED
    ).count()

    # =====================================================
    # USERS
    # =====================================================

    users = (
        User.objects
        .filter(is_active=True)
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        "tasks": page_obj,

        "page_obj": page_obj,

        "paginator": paginator,

        "is_paginated": page_obj.has_other_pages(),

        "users": users,

        "keyword": keyword,

        "total_tasks": total_tasks,

        "pending_tasks": pending_tasks,

        "completed_tasks": completed_tasks,
    }

    return render(
        request,
        "work_tasks/work_task_list.html",
        context
    )


# =========================================================
# THÊM CÔNG VIỆC
# =========================================================

@login_required
def work_task_create(request):

    if request.method == "GET":

        users = (
            User.objects
            .filter(is_active=True)
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        context = {
            "users": users,
        }

        return render(
            request,
            "work_tasks/work_task_create.html",
            context
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    work_date = request.POST.get(
        "work_date",
        ""
    ).strip()

    content = request.POST.get(
        "content",
        ""
    ).strip()

    handler_id = request.POST.get(
        "handler",
        ""
    ).strip()

    process_content = request.POST.get(
        "process_content",
        ""
    ).strip()

    if not work_date:
        messages.error(
            request,
            "Chưa nhập ngày."
        )
        return redirect("work_task_create")

    if not content:
        messages.error(
            request,
            "Chưa nhập nội dung công việc."
        )
        return redirect("work_task_create")

    # -----------------------------------------------------
    # TẠO
    # -----------------------------------------------------

    task = WorkTask.objects.create(
        work_date=work_date,
        content=content,
        handler_id=handler_id or None,
        process_content=process_content,
        status=WorkTask.STATUS_PENDING,
    )

    messages.success(
        request,
        f"Đã tạo công việc #{task.id}."
    )

    return redirect("work_task_list")


# =========================================================
# SỬA CÔNG VIỆC
# =========================================================

@login_required
def work_task_update(request, pk):

    task = get_object_or_404(
        WorkTask,
        pk=pk
    )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method == "GET":

        users = (
            User.objects
            .filter(is_active=True)
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        context = {
            "task": task,
            "users": users,
        }

        return render(
            request,
            "work_tasks/work_task_update.html",
            context
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    work_date = request.POST.get(
        "work_date",
        ""
    ).strip()

    content = request.POST.get(
        "content",
        ""
    ).strip()

    handler_id = request.POST.get(
        "handler",
        ""
    ).strip()

    process_content = request.POST.get(
        "process_content",
        ""
    ).strip()

    if not work_date:
        messages.error(
            request,
            "Vui lòng chọn ngày."
        )
        return redirect(
            "work_task_update",
            pk=task.pk
        )

    if not content:
        messages.error(
            request,
            "Vui lòng nhập nội dung công việc."
        )
        return redirect(
            "work_task_update",
            pk=task.pk
        )

    task.work_date = work_date
    task.content = content
    task.handler_id = handler_id or None
    task.process_content = process_content

    task.save()

    messages.success(
        request,
        f"Đã cập nhật công việc #{task.id}."
    )

    return redirect("work_task_list")


# =========================================================
# HOÀN THÀNH
# =========================================================

@login_required
def work_task_complete(request, pk):

    task = get_object_or_404(
        WorkTask,
        pk=pk
    )

    # Không cho hoàn thành lại
    if task.status == WorkTask.STATUS_COMPLETED:

        messages.warning(
            request,
            "Công việc này đã hoàn thành."
        )

        return redirect("work_task_list")

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "work_tasks/work_task_complete.html",
            {
                "task": task
            }
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    process_content = request.POST.get(
        "process_content",
        ""
    ).strip()

    if process_content:
        task.process_content = process_content

    task.status = WorkTask.STATUS_COMPLETED

    task.completed_at = timezone.now()

    task.save(
        update_fields=[
            "process_content",
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    messages.success(
        request,
        f"Công việc #{task.id} đã hoàn thành."
    )

    return redirect("work_task_list")


# =========================================================
# XÓA
# =========================================================

@login_required
def work_task_delete(request, pk):

    task = get_object_or_404(
        WorkTask,
        pk=pk
    )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "work_tasks/work_task_delete.html",
            {
                "task": task
            }
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    task_id = task.id

    task.delete()

    messages.success(
        request,
        f"Đã xóa công việc #{task_id}."
    )

    return redirect("work_task_list")
