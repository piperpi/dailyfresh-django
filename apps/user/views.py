from django.shortcuts import render, HttpResponse, redirect, reverse
from django.views.generic import View
from django.contrib.auth import get_user_model
from .models import Address
from ..goods.models import GoodsSKU
from ..order.models import OrderGoods,OrderInfo
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.utils import IntegrityError
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer
from celery_tasks.tasks import send_login_mail
from django_redis import get_redis_connection
import re


class Register(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        if not all([username, pwd, cpwd, email]) or allow != 'on':
            return render(request, 'register.html', {'errmsg': '参数不完整'})
        if not re.match('[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
        if pwd != cpwd:
            return render(request, 'register.html', {'errmsg': '两次输入的密码不一致'})
        try:
            User = get_user_model()
            user = User.objects.create_user(username, email, pwd, is_active=False)
            user.save()
        except IntegrityError as e:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        except Exception as e:
            return render(request, 'register.html', {'errmsg': '数据库异常'})

        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # bytes
        token = token.decode()
        send_login_mail.delay(email, token)
        return render(request, 'login.html', {'errmsg': '请查收邮件激活用户'})


class Active(View):
    def get(self, request, token):
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600)
        info = serializer.loads(token)
        user_id = info.get('confirm')
        try:
            User = get_user_model()
            User.objects.filter(id=user_id).update(is_active=True)
        except Exception as e:
            return render(request, 'login.html', {'errmsg': '数据库异常'})
        return render(request, 'login.html', {'errmsg': '用户已激活'})


class Login(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '参数不完整'})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                return render(request, 'login.html', {'errmsg': '用户未激活'})
            else:
                login(request, user)
                next_url = request.GET.get('next', reverse('goods:index'))
                print(request.GET)
                print(next_url)
                resp = redirect(next_url)
                print(resp)
                remember = request.POST.get('remember')
                if remember == 'on':
                    resp.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    resp.delete_cookie('username')
                return resp
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class Logout(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


class Info(LoginRequiredMixin, View):
    def get(self, request):
        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        # 获取用户的历史浏览记录
        con = get_redis_connection('default')

        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)

        # 遍历获取用户浏览的商品信息
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}

        # 除了你给模板文件传递的模板变量之外，django框架会把request.user也传给模板文件
        return render(request, 'user_center_info.html', context)


class Order(LoginRequiredMixin, View):
    '''用户中心-订单页'''

    def get(self, request, page):
        '''显示'''
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount,保存订单商品的小计
                order_sku.amount = amount

            # 动态给order增加属性，保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,
                   'page': 'order'}

        # 使用模板
        return render(request, 'user_center_order.html', context)


class AddressView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            address = Address.objects.get(user=request.user)
        except:
            address=None
        return render(request, 'user_center_site.html', {'address': address,'page': 'address',})

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        if not all([receiver, addr, zip_code, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '参数不完整'})
        user = get_user_model().objects.get(id=request.user.id)
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=True,
                               )
        return render(request, 'user_center_site.html')
