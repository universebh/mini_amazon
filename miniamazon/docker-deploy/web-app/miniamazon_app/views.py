from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponse
from .forms import RegisterForm, ProductSearchForm, ProductAmountForm, DeliveryAddressForm
from .models import CreditCard, DeliveryAddress, MyUser, Order, WareHouse, Product, LocalStorage, Cart, OrderCollection
from django.views.generic import DetailView, ListView, DeleteView
from django.shortcuts import get_object_or_404
from collections import defaultdict
import socket
from socket import error as SocketError
from .web_app_config import BACKEND_HOST, BACKEND_PORT, MAX_STORAGE
import datetime
import json
import errno
import os
from copy import deepcopy


# Create your views here.
# amazon user homepage
@login_required
def miniamazonhome(request):
    if request.method == 'POST':
        form = ProductSearchForm(request.POST)
        if form.is_valid():
            product_type = form.cleaned_data.get('product_type')
            product = Product.objects.filter(name=product_type)
            product_id = product[0].product_id
            return redirect('/home/products/' + str(product_id))
        else:
            error_message = 'Invalid Input For Form. Please select among the given products.'
            messages.error(request, error_message)
    else:
        form = ProductSearchForm()
    return render(request, 'miniamazon_app/home.html', {'ProductSearchForm': form})



# about page
def about(request):
    return render(request, 'miniamazon_app/about.html')



# register to be a user
def register(request):
    # subimt the form
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        # valid, then save form database and then redirect to login page
        if form.is_valid():
            form.save()
            dest_x = form.cleaned_data.get('delivery_address_x_coord')
            dest_y = form.cleaned_data.get('delivery_address_y_coord')
            username = form.cleaned_data.get('username')
            # user = get_object_or_404(MyUser, pk=)
            messages.success(request, f'Welcome {username}, your account is created. You can log in now!')
            return redirect('login')
        # invalid, display error message
        else:
            errdict = form.errors.as_data()
            result = set()
            errset = set(errdict.keys())
            for key in errset:
                if key == 'password1' or key == 'password2':
                    result.add('password')
                else:
                    result.add(key)
            error_message = 'Invalid ' + ' '.join(list(result)) + '. Please follow instructions'
            messages.error(request, error_message, extra_tags='html_safe alert alert-danger')


    # fill the form    
    else:
        form = RegisterForm()
    
    # render the form page, pass the register form as context
    return render(request, 'miniamazon_app/register.html', {'RegisterForm': form})



def logout_view(request):
    logout(request)
    if not request.user.is_authenticated:
        messages.success(request, f'You have successfully logged out. You can log in again.')
    return redirect('login')


@login_required
def ProductDetailView(request, product_id):
    if request.method == 'POST':
        form = ProductSearchForm(request.POST)
        if form.is_valid():
            product_type = form.cleaned_data.get('product_type')
            product = Product.objects.filter(name=product_type).first()
            storage = LocalStorage.objects.filter(product=product.product_id)
            context = {"product": product, 'ProductSearchForm': form, "storage": storage}
            #return render(request, 'miniamazon_app/product_detail.html', context)
            return redirect('/home/products/'+str(product.product_id)+'/', context)
        else:
            error_message = 'Invalid Input For Form. Please select among the given products.'
            messages.error(request, error_message)
    else:
        form = ProductSearchForm()
    product = Product.objects.filter(product_id=product_id).first()
    storage = LocalStorage.objects.filter(product=product_id)
    context = {"product": product, 'ProductSearchForm': form, "storage": storage}
    return render(request, 'miniamazon_app/product_detail.html', context)



@login_required
def ProductAmountView(request, product_id, warehouse_id):
    #template_name = 'miniamazon_app/product_amount.html'
    product = Product.objects.filter(product_id=product_id)
    print("Product ID is: {}".format(product_id))
    warehouse = WareHouse.objects.filter(warehouse_id=warehouse_id)
    print("Warehouse ID is: {}".format(warehouse_id))
    if request.method == 'POST':
        form = ProductAmountForm(request.POST)
        if form.is_valid():
            product_amount = form.cleaned_data.get('product_amount')
            db_operation_add_cart(request, product_id, warehouse_id, product_amount)
            cart = Cart.objects.all()
            print("Cart in product amount view is: {}".format(cart))
            return redirect('/home/cart/')
        else:
            error_message = 'Invalid Input For Form. Please enter a positve integer.'
            messages.error(request, error_message)
    else:
        form = ProductAmountForm()
        print(form)
    context = {"product": product, 'form': form, "warehouse": warehouse}
    return render(request, 'miniamazon_app/product_amount.html', context)



# helper method for database operation when clicking on Add To Cart
def db_operation_add_cart(request, product_id, warehouse_id, product_amount):
    # cart table empty
    if not Cart.objects.exists():
        new_cart = Cart.objects.create()
        # print("Cart is {}".format(new_cart))
        new_cart.product.add(product_id)
        new_cart.amount = product_amount
        new_cart.warehouse.add(warehouse_id)
        new_cart.owner = request.user
        new_cart.save()
        # print("updated cart is {}".format(new_cart))
    # cart table not empty
    else:
        for ct in Cart.objects.all():
            # exists a matching row
            if ct.warehouse.first().warehouse_id == warehouse_id and ct.product.first().product_id == product_id:
                ct.amount += product_amount
                ct.save()
                break
            # not match
            else:
                continue
        if ct.warehouse.first().warehouse_id != warehouse_id or ct.product.first().product_id != product_id:
            new_cart = Cart.objects.create()
            new_cart.product.add(product_id)
            new_cart.amount = product_amount
            new_cart.warehouse.add(warehouse_id)
            new_cart.owner = request.user
            new_cart.save()
        


@login_required
def CartListView(request):
    # should only list carts of the current user
    cart = Cart.objects.filter(owner=request.user.id)
    context = {"cart": cart}
    return render(request, 'miniamazon_app/cart.html', context)

# class CartListView(LoginRequiredMixin, ListView):
#     model = Cart
#     template_name = 'miniamazon_app/cart.html'
#     context_object_name = 'cart'

#     # only list carts of the current user, not others
#     def get_queryset(self):
#         qs = Cart.objects.filter(owner=self.request.user.id)
#         return qs



@login_required
def OrderProcessView(request):
    # socket params
    ip = BACKEND_HOST
    port = BACKEND_PORT

    # check storage
    msg_buy_dict, msg_cannot_meet = check_storage(request)

    # local storage not enough after buying, need to buy things from world
    if msg_buy_dict:
        send_msg = json.dumps(msg_buy_dict)
        start = datetime.datetime.now()
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # connect
                s.connect((ip, port))
                curr = datetime.datetime.now()
                duration = curr - start
                # timeout, redirect to cart page
                if duration.seconds > 10:
                    s.close()
                    return redirect('amazon-cart')
                # send
                print('send_msg: {}'.format(send_msg))
                s.send(send_msg.encode('utf-8')) 
                # receive ack and check
                recv_msg = s.recv(65535)
                s.close()
                recv_msg = recv_msg.decode('utf-8')
                print(recv_msg)
                recv_msg_dict = json.loads(recv_msg)
                if recv_msg_dict['acks'] == msg_buy_dict["Cart ID"]:
                    break
            except SocketError as e:
                # socket communication error handling
                s.close()
                print(os.strerror(e.errno))
            except TypeError as e:
                print(os.strerror(e.errno))

    # need not to buy things
    new_order_collection_pk = db_operation_place_order(request, ip, port, msg_buy_dict)
    # filter order, order collection, product
    order = Order.objects.filter(owner=request.user.id)
    if new_order_collection_pk:
        order_collection = OrderCollection.objects.filter(order_collection_id=new_order_collection_pk)
    else:
        order_collection = None
    product = Product.objects.all()
    
    user_order = None
    if order_collection:
        user_order = order.filter(order_collection=order_collection.first().order_collection_id)

    context = {"order": user_order, "order_collection": order_collection, 
            "product": product, "msg_not_met": msg_cannot_meet}
   
    return render(request, 'miniamazon_app/cart_process.html', context)



# helper method to check storage
def check_storage(request):
    # initialize msg dictionary and cannot meet dict
    msg_buy_dict = defaultdict(list)
    msg_cannot_meet = [{},]

    # check storage
    qs = Cart.objects.filter(owner=request.user.id)
    for ct in qs:
        # amount in cart
        amt_cart = ct.amount
        # determine product and warehouse
        pd = ct.product.first().product_id
        wh = ct.warehouse.first().warehouse_id
        # amount in local storage
        for ls in LocalStorage.objects.all():
            if ls.product.first().product_id == pd and ls.warehouse.warehouse_id == wh:
                amt_ls = ls.storage
                # cart amount exceeds warehouse storage limit
                if amt_cart > MAX_STORAGE:
                    new_dict = {}
                    new_dict['Warehouse ID'] = wh
                    new_dict['Product Name'] = Product.objects.filter(product_id=pd).first().name
                    new_dict['Maximal Allowed Amount'] = MAX_STORAGE
                    msg_cannot_meet.append(new_dict)
                # compare local storage and amount in cart
                # left = amt_ls - amt_cart
                elif amt_ls - amt_cart < 20:
                    left = amt_ls - amt_cart
                    msg_buy_dict['Warehouse ID'].append(wh)
                    msg_buy_dict['Product Name'].append(Product.objects.filter(product_id=pd).first().name)
                    msg_buy_dict['Product ID'].append(pd)
                    msg_buy_dict['Amount To Purchase'].append(MAX_STORAGE - left)
                    msg_buy_dict['Cart ID'].append(ct.cart_id)
                    msg_buy_dict['Local Storage ID'].append(ls.local_storage_id)
    
    return msg_buy_dict, msg_cannot_meet



# helper method for truck call
def truck_call_and_pack(request, ip, port, msg_buy_dict, order_collection_pk):
    start = datetime.datetime.now()
    while True:
        try:
            # create socket and connect
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            curr = datetime.datetime.now()
            duration = curr - start
            if duration.seconds > 10:
                s.close()

            # build truck call message
            # order id, warehouse id, deliver x, deliver y
            msg_truckcall_dict = defaultdict(list)
            msg_truckcall_dict["Package ID"].append(order_collection_pk)
            msg_truckcall_dict["Warehouse ID"].append(WareHouse.objects.first().warehouse_id)
            delivery_addr = MyUser.objects.filter(id=request.user.id).first().delivery_address
            msg_truckcall_dict["Delivery x"].append(delivery_addr.x)
            msg_truckcall_dict["Delivery y"].append(delivery_addr.y)
            msg_truckcall_dict["Owner"].append(request.user.id)

            # product id, product description, count
            product_id_list, product_desc_list, product_count_list = [], [], []
            for ct in Cart.objects.filter(owner=request.user.id):
                msg_truckcall_dict["Product ID"].append(ct.product.first().product_id)
                msg_truckcall_dict["Product Description"].append(ct.product.first().name)
                msg_truckcall_dict["Count"].append(ct.amount)
            # print(msg_truckcall_dict)

            # send msg to interface server
            print('send_msg: {}'.format(msg_truckcall_dict))
            s.send(json.dumps(msg_truckcall_dict).encode('utf-8'))

            # receive ack and check
            recv_msg = s.recv(65535)
            s.close()
            recv_msg = recv_msg.decode('utf-8')
            recv_msg_dict = json.loads(recv_msg)
            if recv_msg_dict['acks'] == msg_truckcall_dict["Package ID"]:
                # change the order status to Packing
                order = Order.objects.filter(owner=request.user.id).first()
                order.status = "Packing"
                order.save()
                break
            
        except SocketError as e:
                # socket communication error handling
                s.close()
                print(os.strerror(e.errno))
        
        except TypeError as e:
                print(os.strerror(e.errno))



# warehouse id, product id, product description, count, order id

# helper method for database operation when clicking on Place Order
def db_operation_place_order(request, ip, port, msg_buy_dict):
    for crt in Cart.objects.filter(owner=request.user.id):
        warehouse = crt.warehouse.first()
        product = crt.product.first()
        for ls in LocalStorage.objects.all():
            if ls.warehouse.warehouse_id == warehouse.warehouse_id and ls.product.first().product_id == product.product_id:
                if crt.amount > MAX_STORAGE:
                    crt.delete()
                    # messages.error(request, error_message, extra_tags='html_safe alert alert-danger')
                else:
                    ls.storage -= crt.amount
                    ls.save()
                    product = Product.objects.filter(product_id=ls.product.first().product_id).first()
                    product.storage -= crt.amount
                    product.save()

    new_order_collection_pk = None

    if Cart.objects.filter(owner=request.user.id).count() != 0:
        # create order collection
        new_order_collection = OrderCollection.objects.create()
        # create order, status, owner, warehouse, amount, order collection
        for crt in Cart.objects.filter(owner=request.user.id):
            for wh in crt.warehouse.all():
                new_order = Order.objects.create()
                new_order.owner = request.user
                new_order.warehouse.add(wh.warehouse_id)
                new_order.amount = crt.amount
                # print("123{}.".format(new_order.order_collection))
                # print("456{}.".format(new_order_collection.order_collection_id))
                new_order.order_collection = new_order_collection
                new_order.save()
        new_order_collection.status = 'Placed'
        new_order_collection.owner = request.user
        new_order_collection.save()
        new_order_collection_pk = new_order_collection.order_collection_id


        for crt in Cart.objects.filter(owner=request.user.id):
            for pd in crt.product.all():
                pd.order.add(new_order.order_id)
                pd.save()
            #crt.delete()
        # call truck
        truck_call_and_pack(request, ip, port, msg_buy_dict, new_order_collection_pk)
        for crt in Cart.objects.filter(owner=request.user.id):
            crt.delete()
    return new_order_collection_pk



# list the current order
@login_required
def OrderListView(request):
    order_collection = OrderCollection.objects.filter(owner=request.user.id)
    context = {"order_collection": order_collection}
    return render(request, 'miniamazon_app/order_history.html', context)



# Delivery address
@login_required
def AddressView(request):
    user = MyUser.objects.filter(id=request.user.id)
    delivery_addr = user.first().delivery_address
    context = {"delivery_addr": delivery_addr}
    return render(request, 'miniamazon_app/delivery_addr.html', context)



# Change delivery address
@login_required
def changeaddress(request):
    user = get_object_or_404(MyUser, pk=request.user.id)
    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)
        if form.is_valid():
            delivery_address = user.delivery_address
            delivery_address.x = form.cleaned_data.get('x')
            delivery_address.y = form.cleaned_data.get('y')
            delivery_address.save()
            return redirect('delivery-addr')
        else:
            error_message = 'Invalid Input For Form. Please select among the given products.'
            messages.error(request, error_message)
    else:
        form = DeliveryAddressForm(initial={'x': user.delivery_address.x, 'y': user.delivery_address.y})
    return render(request, 'miniamazon_app/change_delivery_addr.html', {'DeliveryAddressForm': form})    



# delete cart
class CartDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Cart
    template_name = 'miniamazon_app/cart_delete.html'
    success_url = '/home/'

    def delete(self, request, *args, **kwargs):
        # if self.get_object().status == "open":
        #     return super(CartDeleteView, self).delete(request, *args, **kwargs)
        # else:
        #     error_message = "You cannot cancel a confirmed ride"
        #     messages.error(request, error_message, extra_tags='html_safe alert alert-danger')
        #     return redirect('/home/activities')
        return super(CartDeleteView, self).delete(request, *args, **kwargs)

    def test_func(self):
        cart = self.get_object()
        if self.request.user == cart.owner:
            return True
        return False



# Order Detail including product name, warehouse ID, amount
@login_required
def OrderDetailView(request, pk):
    oc_filtered = OrderCollection.objects.filter(order_collection_id=pk)
    pd_name = []
    amt = []
    # ordercollection -> order -> product
    for oc in Order.objects.all():
        if oc.order_collection == oc_filtered.first():
            for pd in Product.objects.all():
                for od_in_pd in pd.order.all():
                    if od_in_pd == oc:
                        pd_name.append(pd.name)
    # ordercollection -> order -> warehouse
    # for oc in Order.objects.all():
    #     if oc.order_collection == oc_filtered.first():
    #         for wh_in_order in oc.warehouse.all():
    #             for pd in Product.objects.all():
    #                 for wh_in_pd in pd.warehouse.all():
    #                     if wh_in_pd == wh_in_order:
    #                         wh_id.append(wh_in_pd)
    # ordercollection -> order -> amount
    for oc in Order.objects.all():
        if oc.order_collection == oc_filtered.first():
            amt.append(oc.amount)
    wh_id = [1] * len(pd_name)
    # print(pd_name, wh_id, amt)
    assert len(pd_name) == len(wh_id) == len(amt)
    # [pd_name, wh_id, amt]
    order_collection_data = []
    for i in range(len(pd_name)):
        order_data = [pd_name[i], wh_id[i], amt[i]]
        order_collection_data.append(order_data)
    
    context = {"order_collection_data": order_collection_data}
    return render(request, 'miniamazon_app/order_detail.html', context)    
