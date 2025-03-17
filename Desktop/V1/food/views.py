import os
import qrcode
import uuid
import json
from django.shortcuts import render
from math import ceil
from .models import Table, Dish, Order, OrderItem, Invoice
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count, Prefetch, Sum
from django.urls import reverse
from django.conf import settings

# Create your views here.
def order_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'order_status.html', {'order': order})


def order(request):
    # Retrieve dishes in the selected package
    dishes = Dish.objects.all()

    return render(request, 'order.html', {
        'dishes': dishes
    })


def homepage(request):
    error = None
    qr_image_path = None
    group_order_id = None

    # Check if the package is already selected
    selected_package = request.session.get('selected_package', None)

    if request.method == 'POST':
        # Handle package selection
        if 'package' in request.POST:
            package_price = request.POST.get('package')
            request.session['selected_package'] = package_price
            return redirect('homepage')

        # Handle QR code generation and table assignment
        elif 'num_customers' in request.POST:
            num_customers = request.POST.get('num_customers')
            if not num_customers or not num_customers.isdigit():
                error = "Valid number of customers is required."
            else:
                num_customers = int(num_customers)
                available_tables = Table.objects.filter(is_occupied=False)
                table_to_assign = None
                for table in available_tables:
                    if table.capacity >= num_customers:
                        table_to_assign = table
                        break

                if table_to_assign:
                    table_to_assign.is_occupied = True
                    table_to_assign.save()
                    group_order_id = str(uuid.uuid4())
                    qr_image_path = generate_qr_image(group_order_id)
                    Order.objects.create(
                        table=table_to_assign,
                        order_id=group_order_id,
                        total_price=int(selected_package),
                    )
                else:
                    error = "No single table is available to accommodate the specified number of customers."

    return render(request, 'homepage.html', {
        'error': error,
        'selected_package': selected_package,
        'qr_image_path': qr_image_path,
        'group_order_id': group_order_id,
    })

def generate_qr_image(group_order_id):
    # Generate the order page URL dynamically
    order_page_url = f"{settings.SITE_URL}{reverse('order_page', args=[group_order_id])}"

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(order_page_url)  # Embed the URL
    qr.make(fit=True)

    qr_image_relative_path = os.path.join('qrcodes', f'group_order_{group_order_id}.png')
    qr_image_path = os.path.join(settings.MEDIA_ROOT, qr_image_relative_path)
    
    # Ensure the qrcodes directory exists; create it if it doesn't
    os.makedirs(os.path.dirname(qr_image_path), exist_ok=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    qr_image.save(qr_image_path)

    return os.path.join(settings.MEDIA_URL, qr_image_relative_path)

def order_page(request, order_id):
    # Retrieve the selected package from the session
    selected_package = request.session.get('selected_package', None)
    if not selected_package:
        return redirect('homepage')

    # Fetch the existing order
    order = get_object_or_404(Order, order_id=order_id)

    # Retrieve dishes in the selected package
    dishes = Dish.objects.filter(category=selected_package)

    return render(request, 'order_page.html', {
        'order': order,
        'dishes': dishes,
        'selected_package': selected_package,
    })


def kitchen_orders(request):
    # Retrieve orders containing items that are not 'Finished' or 'Cancelled'
    orders = Order.objects.prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.filter(status__in=['Pending', 'Cooking', 'Ready to Serve'])
        )
    ).filter(
        items__status__in=['Pending', 'Cooking', 'Ready to Serve']
    ).distinct().order_by('table__table_number')

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('new_status')

        if 'item_id' in request.POST:
            # Update a specific item
            item_id = request.POST.get('item_id')
            order_item = get_object_or_404(OrderItem, id=item_id, order__order_id=order_id)
            order_item.status = new_status
            order_item.save()
        else:
            # Update all items in the order
            order = get_object_or_404(Order, order_id=order_id)
            order.items.filter(status__in=['Pending', 'Cooking', 'Ready to Serve']).update(status=new_status)

        return redirect('kitchen_orders')

    return render(request, 'kitchen_orders.html', {'orders': orders})

#def kitchen_orders(request):
    # Retrieve orders containing items that are not canceled
    orders = Order.objects.prefetch_related(
        Prefetch('items', queryset=OrderItem.objects.exclude(status='Cancelled'))
    ).filter(
        items__status__in=['Pending', 'Cooking', 'Ready to Serve']
    ).distinct().order_by('table__table_number')

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('new_status')

        if 'item_id' in request.POST:
            # Update a specific item
            item_id = request.POST.get('item_id')
            order_item = get_object_or_404(OrderItem, id=item_id, order__order_id=order_id)
            order_item.status = new_status
            order_item.save()
        else:
            # Update all items in the order
            order = get_object_or_404(Order, order_id=order_id)
            order.items.exclude(status='Cancelled').update(status=new_status)

        return redirect('kitchen_orders')

    return render(request, 'kitchen_orders.html', {'orders': orders})


def submit_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)

        items = data.get('items', [])
        if not items:
            return JsonResponse({'success': False, 'error': 'No items in cart.'}, status=400)

        submitted_items = []
        for item in items:
            try:
                dish = Dish.objects.get(id=item['dishId'], category=request.session.get('selected_package'))
                existing_item = OrderItem.objects.filter(order=order, dish=dish, status='Cancelled').first()
                if existing_item:
                    existing_item.status = OrderItem.PENDING
                    existing_item.quantity = item['quantity']
                    existing_item.additional_option = item.get('additional_option', '')
                    existing_item.save()
                    submitted_items.append(existing_item)
                else:
                    new_item = OrderItem.objects.create(
                        order=order,
                        dish=dish,
                        quantity=item['quantity'],
                        additional_option=item.get('additional_option', ''),
                        status=OrderItem.PENDING
                    )
                    submitted_items.append(new_item)
            except Dish.DoesNotExist:
                return JsonResponse({'success': False, 'error': f"Dish with ID {item['dishId']} not found."}, status=400)

        return JsonResponse({'success': True, 'order_id': order.order_id})

    submitted_items = order.items.filter(status=OrderItem.PENDING)
    return render(request, 'submit_order.html', {
        'order_id': order_id,
        'submitted_items': submitted_items
    })

def change_package(request, order_id):
    error = None

    # Fetch the order using the 'order_id'
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'POST':
        # Get the selected package price from POST data
        package_price = request.POST.get('package')
        valid_packages = ['279', '379']  # List of valid package prices

        if not package_price:
            error = "Package selection is required."
        elif package_price not in valid_packages:
            error = "Invalid package selected. Please try again."
        else:
            # Update session and order details with the new package
            request.session['selected_package'] = package_price
            order.total_price = int(package_price)

            # Optionally clear current order items if the package changes dish options
            order.items.all().delete()  # Optional, based on business logic
            
            # Save the updated order
            order.save()

            # Redirect to the order page with the updated order ID
            return redirect('order_page', order_id=order.order_id)

    return render(request, 'change_package.html', {
        'error': error,
        'selected_package': request.session.get('selected_package', None),
        'order': order,
    })


def checkout(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    
    # Group items by dish name and sum their quantities
    grouped_items = (
        order.items.values('dish__name', 'dish__price')  # Group by dish name and price
        .annotate(total_quantity=Sum('quantity'))        # Sum up the quantities
    )
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount_paid = order.total_price

        # Create an invoice
        invoice = Invoice.objects.create(order=order, payment_method=payment_method, amount_paid=amount_paid, status='Paid')
        order.status = 'Finished'
        order.table.is_occupied = False  # Free up the table
        order.table.save()
        order.save()
        return redirect('homepage')  # Redirect to homepage for the next customer

    return render(request, 'checkout.html', {'order': order, 'grouped_items': grouped_items})