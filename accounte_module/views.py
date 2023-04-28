from django.shortcuts import redirect
from django.contrib.auth import get_user_model # زمانی که یک user جنگو سفارشی درست میکنیم باید به این شکل مدل user را معرفی کنیم
from .serializers import UserRegisterSerializers
from rest_framework.views import APIView
from django.http import HttpRequest, Http404,HttpResponseNotFound
from rest_framework_simplejwt.tokens import RefreshToken #برای درست کردن توکن jwt قبل از ریجیستر
from rest_framework.response import Response
from rest_framework import status
from django.utils.crypto import get_random_string
from django.views import View
import smtplib
from email.message import EmailMessage
from rest_framework.throttling import AnonRateThrottle,UserRateThrottle
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth import login,logout
#Create your views here.


def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh' : str(refresh),
        'access' : str(refresh.access_token),
    }
User =get_user_model() # زمانی که یک user جنگو سفارشی درست میکنیم باید به این شکل مدل user را معرفی کنیم

class UserRegisterView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly,]
    serializer_class =UserRegisterSerializers
    throttle_classes = [UserRateThrottle,AnonRateThrottle]
    """
    create a new user
    
    """
    def post(self,request:HttpRequest):
        ser_date = UserRegisterSerializers(data=request.POST)
        if ser_date.is_valid():
            user_email = ser_date.validated_data.get('email')
            user_password = ser_date.validated_data.get('password')
            user : bool = User.objects.filter(email__iexact=user_email).exists()
            if user == True:
                return Response({'error message': 'ایمیل وارد شده تکراری می باشد'},status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                random_str=get_random_string(84)
                new_user = User(email=user_email,username=user_email,is_active=False,email_active_code=random_str)
                new_user.set_password(user_password)
                # get_token_for_user(new_user)
                new_user.save()
                EMAIL_HOST_PASSWORD = 'qjvhrbqewwvqxmxp'
                EMAIL_HOST = 'smtp.gmail.com'
                EMAIL_HOST_USER = 'testingmyworksdjango@gmail.com'
                EMAIL_PORT_SSL = 465
                msg = EmailMessage()
                msg['Subject'] = 'Activate account'
                msg['Form'] = EMAIL_HOST_USER
                msg['To'] = user_email
                msg.set_content(f'http://localhost:8000/account/activate-account/{random_str}')
                with smtplib.SMTP_SSL(EMAIL_HOST,EMAIL_PORT_SSL) as server:
                    server.login(EMAIL_HOST_USER,EMAIL_HOST_PASSWORD)
                    server.send_message(msg)
                return Response(data=ser_date.data,status=status.HTTP_201_CREATED)
        return Response(data=ser_date.errors,status=status.HTTP_406_NOT_ACCEPTABLE)


class ActivateAccountView(View):
    def get(self,request,email_active_code):
        user : User = User.objects.filter(email_active_code__iexact = email_active_code).first()
        if user is not None:
                user.is_active = True
                print('activated')
                user.email_active_code = get_random_string(84)
                user.save()
                return redirect('http://localhost:8000')
        return HttpResponseNotFound('error')


class UserLoginView(APIView):
    def post(self,request):
        ser_data = UserRegisterSerializers(data=request.POST)
        if ser_data.is_valid():
            user_email = ser_data.validated_data.get('email')
            user_password = ser_data.validated_data.get('password')
            user : User = User.objects.filter(email=user_email).first()
            if user is not None:
                if not user.is_active:
                    return Response({'message' : 'اکانت شما فعال نشده است'},status=status.HTTP_406_NOT_ACCEPTABLE)
                else:
                    if user_email == user.email:
                        check_password = user.check_password(user_password)
                        if check_password:
                            login(request,user)
                            return Response(ser_data.data,status=status.HTTP_202_ACCEPTED)
                        return Response({'message': 'کلمه عبور وارد شده اشتباه است'},status=status.HTTP_400_BAD_REQUEST)
                    return Response({'message': 'ایمیل وارد شده اشتباه است'},status=status.HTTP_406_NOT_ACCEPTABLE)
            return Response({'message' : 'کاربری با مشخصات شما یافت نشده است'},status=status.HTTP_406_NOT_ACCEPTABLE)
        return Response(data=ser_data.errors,status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(View):
    def get(self,request):
        logout(request)
        print('logout shod')
        return redirect('http://localhost:8000')

class UserRestPasswordView(View):
    pass
