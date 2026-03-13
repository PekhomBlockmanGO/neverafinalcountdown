import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
import base64
from io import BytesIO

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.db.models import Count, F, ExpressionWrapper, DurationField
from django.conf import settings

from tickets.models import Ticket, TicketLog
from masters.models import Site, Area, Location, SpecificArea
from .models import EmergencyContact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_user_role(user):
    """Return 'Admin', 'Manager', or 'Client'."""
    if user.is_superuser:
        return "Admin"
    elif user.groups.filter(name__iexact="Manager").exists():
        return "Manager"
    return "Client"


def _is_staff_or_admin(user):
    return user.is_superuser or user.groups.filter(name__iexact="Manager").exists()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    role = get_user_role(request.user)
    tickets = Ticket.objects.select_related('site', 'area', 'location', 'specific_area').all()

    return render(request, "accounts/dashboard.html", {
        "tickets": tickets,
        "role": role,
        "server_time": timezone.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# Daily Insights
# ---------------------------------------------------------------------------

@login_required
def daily_insights(request):
    role = get_user_role(request.user)
    today = timezone.localdate()
    today_tickets = Ticket.objects.filter(created_at__date=today)
    total_today = today_tickets.count()

    category_data = (
        today_tickets.values("category").annotate(count=Count("id")).order_by("category")
    )
    status_data = today_tickets.values("status").annotate(count=Count("id"))

    status_percentages = {
        item["status"]: round((item["count"] / total_today) * 100, 1) if total_today else 0
        for item in status_data
    }

    return render(request, "accounts/daily_insights.html", {
        "role": role,
        "page_title": "Daily Insights",
        "total_today": total_today,
        "category_labels": [c["category"] for c in category_data],
        "category_counts": [c["count"] for c in category_data],
        "status_labels": list(status_percentages.keys()),
        "status_percentages": list(status_percentages.values()),
    })


# ---------------------------------------------------------------------------
# Operational Analytics
# ---------------------------------------------------------------------------

@login_required
def operational_analytics(request):
    role = get_user_role(request.user)
    all_tickets = Ticket.objects.all()
    total_tickets = all_tickets.count()

    category_data = (
        all_tickets.values("category").annotate(count=Count("id")).order_by("category")
    )
    status_data = all_tickets.values("status").annotate(count=Count("id"))

    status_percentages = {
        item["status"]: round((item["count"] / total_tickets) * 100, 1) if total_tickets else 0
        for item in status_data
    }

    return render(request, "accounts/operational_analytics.html", {
        "role": role,
        "page_title": "Operational Analytics",
        "total_tickets": total_tickets,
        "category_labels": [c["category"] for c in category_data],
        "category_counts": [c["count"] for c in category_data],
        "status_labels": list(status_percentages.keys()),
        "status_percentages": list(status_percentages.values()),
    })


# ---------------------------------------------------------------------------
# Ticket: Update Status
# ---------------------------------------------------------------------------

@login_required
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    user = request.user

    if not _is_staff_or_admin(user):
        messages.error(request, "You do not have permission to update tickets.")
        return redirect("accounts:dashboard")

    if request.method != "POST":
        return redirect("accounts:dashboard")

    new_status = request.POST.get("status", "").strip()
    new_remarks = request.POST.get("remarks", "").strip()
    STATUS_FLOW = ["Open", "Attended", "In Progress", "Delayed", "Closed"]

    if new_status not in STATUS_FLOW:
        messages.error(request, "Invalid status value.")
        return redirect("accounts:dashboard")

    current_index = STATUS_FLOW.index(ticket.status)
    new_index = STATUS_FLOW.index(new_status)
    old_status = ticket.status

    if user.is_superuser:
        ticket.status = new_status
    elif user.groups.filter(name__iexact="Manager").exists():
        if new_index < current_index:
            messages.error(request, "Managers cannot revert a ticket status.")
            return redirect("accounts:dashboard")
        ticket.status = new_status

    if new_status == "Delayed" and new_remarks:
        ticket.remarks = new_remarks

    ticket.save()

    if old_status != new_status:
        log_remarks = (
            new_remarks if new_status == "Delayed"
            else f"Status updated to '{new_status}' by {user.username}"
        )
        TicketLog.objects.create(
            ticket=ticket,
            status=new_status,
            remarks=log_remarks,
        )

    messages.success(request, f"Ticket #{ticket.id} updated to '{new_status}'.")
    return redirect("accounts:dashboard")


# ---------------------------------------------------------------------------
# Ticket: Delete
# ---------------------------------------------------------------------------

@login_required
def delete_ticket(request, ticket_id):
    if not request.user.is_superuser:
        messages.error(request, "Only admins can delete tickets.")
        return redirect("accounts:dashboard")

    if request.method != "POST":
        return redirect("accounts:dashboard")

    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket_id_display = ticket.id
    ticket.delete()
    messages.success(request, f"Ticket #{ticket_id_display} deleted.")
    return redirect("accounts:dashboard")


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@login_required
def audit_logs(request):
    role = get_user_role(request.user)

    if role not in ("Admin", "Manager"):
        messages.error(request, "Access restricted.")
        return redirect("accounts:dashboard")

    logs = (
        TicketLog.objects
        .select_related('ticket', 'ticket__location', 'ticket__area')
        .order_by('-timestamp')
    )

    # Compute resolution time only for Closed logs — avoids per-row Python math
    for log in logs:
        log.time_taken_hours = None
        if log.status == "Closed" and log.ticket.created_at:
            diff = log.timestamp - log.ticket.created_at
            log.time_taken_hours = round(diff.total_seconds() / 3600, 2)

    return render(request, "accounts/audit_logs.html", {
        "logs": logs,
        "role": role,
    })


# ---------------------------------------------------------------------------
# Manage Masters (Admin only)
# ---------------------------------------------------------------------------

@login_required
def manage_masters(request):
    role = get_user_role(request.user)

    if role != "Admin":
        messages.error(request, "This section is restricted to Admins.")
        return redirect("accounts:dashboard")

    def _build_context():
        return {
            "role": role,
            "sites": Site.objects.all(),
            "areas": Area.objects.select_related('site').all(),
            "locations": Location.objects.select_related('area__site').all(),
            "specific_areas": SpecificArea.objects.all(),
            "users": User.objects.prefetch_related('groups').all(),
            "groups": Group.objects.all(),
            "emergency_contact": EmergencyContact.get_solo(),
        }

    context = _build_context()

    if request.method == "POST":
        form_type = request.POST.get("form_type", "")
        context.update(_handle_master_post(request, form_type, context))
        # Refresh master data after any change
        context.update(_build_context())

    return render(request, "accounts/manage_masters.html", context)


def _handle_master_post(request, form_type, context):
    """Dispatch POST handlers for manage_masters. Returns extra context dict."""
    extra = {}

    if form_type == "add_site":
        site_name = request.POST.get("site_name", "").strip()
        if site_name:
            Site.objects.create(name=site_name)
            messages.success(request, f"Site '{site_name}' added.")

    elif form_type == "add_area":
        site_id = request.POST.get("site_id")
        area_name = request.POST.get("area_name", "").strip()
        if site_id and area_name:
            site = get_object_or_404(Site, id=site_id)
            Area.objects.create(site=site, name=area_name)
            messages.success(request, f"Building '{area_name}' added to {site.name}.")

    elif form_type == "add_location":
        area_id = request.POST.get("area_id")
        location_name = request.POST.get("location_name", "").strip()
        if area_id and location_name:
            area = get_object_or_404(Area, id=area_id)
            Location.objects.create(area=area, name=location_name)
            messages.success(request, f"Floor '{location_name}' added.")

    elif form_type == "add_specific_area":
        specific_area_name = request.POST.get("specific_area_name", "").strip()
        if specific_area_name:
            SpecificArea.objects.create(name=specific_area_name)
            messages.success(request, f"Specific area '{specific_area_name}' added.")

    elif form_type == "generate_qr":
        extra = _handle_generate_qr(request, context)

    elif form_type == "create_user":
        _handle_create_user(request)

    elif form_type == "delete_user":
        user_id = request.POST.get("user_id")
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if user and user != request.user:
                user.delete()
                messages.success(request, "User deleted.")
            elif user == request.user:
                messages.error(request, "You cannot delete your own account.")

    elif form_type == "create_group":
        group_name = request.POST.get("group_name", "").strip()
        if group_name:
            _, created = Group.objects.get_or_create(name=group_name)
            if created:
                messages.success(request, f"Group '{group_name}' created.")

    elif form_type == "delete_group":
        group_id = request.POST.get("group_id")
        if group_id:
            Group.objects.filter(id=group_id).delete()
            messages.success(request, "Group deleted.")

    elif form_type == "update_emergency":
        phone_number = request.POST.get("phone_number", "").strip()
        if phone_number.isdigit() and len(phone_number) == 10:
            contact = EmergencyContact.get_solo()
            contact.phone_number = phone_number
            contact.save()
            messages.success(request, "Emergency number updated successfully.")
        else:
            messages.error(request, "Phone number must be exactly 10 digits.")

    return extra


def _handle_generate_qr(request, context):
    """Generate a preview QR code and return it as extra context."""
    qr_site = request.POST.get("qr_site")
    qr_area = request.POST.get("qr_area")
    qr_location = request.POST.get("qr_location")
    qr_room = request.POST.get("qr_room")

    if not all([qr_site, qr_area, qr_location, qr_room]):
        messages.error(request, "Please select all QR fields.")
        return {}

    site = get_object_or_404(Site, id=qr_site)
    area = get_object_or_404(Area, id=qr_area)
    location = get_object_or_404(Location, id=qr_location)
    room = get_object_or_404(SpecificArea, id=qr_room)

    base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    qr_text = f"{base_url}/tickets/q/{location.qr_token}/"

    qr = qrcode.QRCode(
        version=1, error_correction=ERROR_CORRECT_H, box_size=10, border=4
    )
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "qr_data": qr_base64,
        "qr_site_name": site.name,
        "qr_location_name": location.name,
        "qr_room_name": room.name,
    }


def _handle_create_user(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")
    is_superuser = request.POST.get("is_superuser") == "on"
    group_ids = request.POST.getlist("groups")

    if not username or not password:
        messages.error(request, "Username and password are required.")
        return

    if User.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' already exists.")
        return

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_superuser = is_superuser
    user.is_staff = is_superuser
    user.save()
    if group_ids:
        user.groups.set(group_ids)
    messages.success(request, f"User '{username}' created.")


# ---------------------------------------------------------------------------
# Manage Users / Groups (kept as separate views for URL clarity)
# ---------------------------------------------------------------------------

@login_required
def manage_users(request):
    if not request.user.is_superuser:
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/manage_users.html", {
        "users": User.objects.prefetch_related('groups').all(),
        "groups": Group.objects.all(),
    })


@login_required
def manage_groups(request):
    if not request.user.is_superuser:
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/manage_groups.html", {
        "groups": Group.objects.all(),
    })


# ---------------------------------------------------------------------------
# Emergency Page (public)
# ---------------------------------------------------------------------------

def emergency_view(request):
    contact = EmergencyContact.objects.first()
    return render(request, "accounts/emergency.html", {"contact": contact})
