from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from masters.models import Location, Area
from .forms import QRComplaintForm
from .models import TicketLog, Ticket
from accounts.models import EmergencyContact


# ---------------------------------------------------------------------------
# QR / Manual Complaint View
# ---------------------------------------------------------------------------
def qr_complaint_view(request, token=None):
    location_obj = None
    is_qr = False
    initial_data = {}
    site_name = "New Docket Form"

    if token:
        # QR-code scan flow
        location_obj = get_object_or_404(Location, qr_token=token, qr_enabled=True)
        initial_data = {
            'area': location_obj.area,
            'location': location_obj,
            'specific_area': location_obj.specific_area,
        }
        site_name = location_obj.area.site.name
        is_qr = True

    elif request.GET.get('area') and request.GET.get('location'):
        # Manual entry with pre-filled params (e.g. admin shortcut)
        area_id = request.GET.get('area')
        area_obj = get_object_or_404(Area, id=area_id)
        site_name = area_obj.site.name
        initial_data = {
            'area': area_id,
            'location': request.GET.get('location'),
            'specific_area': request.GET.get('room'),
        }
        is_qr = True

    if request.method == 'POST':
        form = QRComplaintForm(
            request.POST, request.FILES, initial=initial_data, is_qr=is_qr
        )
        if form.is_valid():
            ticket = form.save(commit=False)

            # Safely derive site from area — guard against area being None
            if ticket.area:
                ticket.site = ticket.area.site
            else:
                # Fallback: derive site from location's area
                ticket.site = ticket.location.area.site

            ticket.source = 'QR' if is_qr else 'Manual'
            ticket.save()

            TicketLog.objects.create(
                ticket=ticket,
                status='Open',
                remarks='Ticket created via Docket Form',
            )

            return redirect('tickets:success')
    else:
        form = QRComplaintForm(initial=initial_data, is_qr=is_qr)

    emergency_contact = EmergencyContact.objects.first()

    return render(request, 'tickets/complaint_form.html', {
        'form': form,
        'is_qr': is_qr,
        'location_obj': location_obj,
        'site_name': site_name,
        'emergency_contact': emergency_contact,
    })


# ---------------------------------------------------------------------------
# Real-time Notification Checker (login required — do not expose publicly)
# ---------------------------------------------------------------------------
@login_required
def check_new_tickets(request):
    last_check_str = request.GET.get('last_check')

    if not last_check_str:
        return JsonResponse({'new': False, 'timestamp': timezone.now().isoformat()})

    last_check = parse_datetime(last_check_str)

    if not last_check:
        return JsonResponse({'new': False, 'timestamp': timezone.now().isoformat()})

    if timezone.is_naive(last_check):
        last_check = timezone.make_aware(last_check)

    latest_ticket = (
        Ticket.objects.filter(created_at__gt=last_check)
        .order_by('-created_at')
        .first()
    )

    if latest_ticket:
        return JsonResponse({
            'new': True,
            'latest_id': latest_ticket.id,
            'timestamp': timezone.now().isoformat(),
        })

    return JsonResponse({'new': False, 'timestamp': timezone.now().isoformat()})


# ---------------------------------------------------------------------------
# Emergency Contact Page
# ---------------------------------------------------------------------------
def emergency_view(request):
    contact = EmergencyContact.objects.first()
    return render(request, 'tickets/emergency.html', {'contact': contact})

# ---------------------------------------------------------------------------
# Success View
# ---------------------------------------------------------------------------
def success_view(request):
    return render(request, 'tickets/success.html')
