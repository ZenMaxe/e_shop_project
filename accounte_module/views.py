from django.shortcuts import redirect
from django.contrib.auth import \
    get_user_model  # زمانی که یک user جنگو سفارشی درست میکنیم باید به این شکل مدل user را معرفی کنیم
from .permissions import PermissionEditUserProfile
from .serializers import *
from rest_framework.views import APIView
from django.http import HttpRequest, Http404, HttpResponseNotFound
from rest_framework_simplejwt.tokens import RefreshToken  # برای درست کردن توکن jwt قبل از ریجیستر
from rest_framework.response import Response
from rest_framework import status
from django.utils.crypto import get_random_string
from django.views import View
import smtplib
from email.message import EmailMessage
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.contrib.auth import login, logout
from .config import *

# Create your views here.


def get_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


User = get_user_model()  # زمانی که یک user جنگو سفارشی درست میکنیم باید به این شکل مدل user را معرفی کنیم


class UserRegisterView(APIView):
    serializer_class = UserRegisterSerializer
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    """
    create a new user (user register page)
    
    """

    def post(self, request: HttpRequest):
        ser_date = UserRegisterSerializer(data=request.POST)
        if not ser_date.is_valid():
            return Response(data=ser_date.errors, status=status.HTTP_406_NOT_ACCEPTABLE)

        user_email = ser_date.validated_data.get('email')
        user_password = ser_date.validated_data.get('password')
        user: bool = User.objects.filter(email__iexact=user_email).exists()
        if user:
            return Response({'error message': 'ایمیل وارد شده تکراری می باشد'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        random_str = get_random_string(84)
        new_user = User(email=user_email, username=user_email, is_active=False, email_active_code=random_str)
        new_user.set_password(user_password)
        # get_token_for_user(new_user)
        new_user.save()

        msg = EmailMessage()
        msg['Subject'] = 'Activate account'
        msg['Form'] = EMAIL_HOST_USER
        msg['To'] = user_email
        msg.set_content(f'http://localhost:8000/account/activate-account/{random_str}')
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT_SSL) as server:
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        return Response(data=ser_date.data, status=status.HTTP_201_CREATED)


class ActivateAccountView(View):
    def get(self, request, email_active_code):
        user: User = User.objects.filter(email_active_code__iexact=email_active_code).first()
        if user is None:
            return HttpResponseNotFound('error')

        user.is_active = True
        print('activated')
        user.email_active_code = get_random_string(84)
        user.save()
        return redirect('http://localhost:8000')



class UserLoginView(APIView):
    serializer_class = UserLoginSerializer
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    """
    page login view  
    """

    def post(self, request):
        ser_data = UserLoginSerializer(data=request.POST)
        if not ser_data.is_valid():
            return Response(data=ser_data.errors, status=status.HTTP_400_BAD_REQUEST)

        user_email = ser_data.validated_data.get('email')
        user_password = ser_data.validated_data.get('password')
        user: User = User.objects.filter(email=user_email).first()
        if user is  None:
            return Response({'message': 'کاربری با مشخصات شما یافت نشده است'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if not user.is_active:
            return Response({'message': 'اکانت شما فعال نشده است'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if user_email != user.email:
            return Response({'message': 'ایمیل وارد شده اشتباه است'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        check_password = user.check_password(user_password)
        if not check_password:
            return Response({'message': 'کلمه عبور وارد شده اشتباه است'},
                            status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(ser_data.data, status=status.HTTP_202_ACCEPTED)






class UserLogoutView(View):
    def get(self, request):
        logout(request)
        print('logout shod')
        return redirect('http://localhost:8000')


class UserForgotPasswordView(APIView):
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    serializer_class = UserForgotPasswordSerializer
    """
    page forget password
    """

    def post(self, request: HttpRequest):
        ser_data = UserForgotPasswordSerializer(data=request.POST)
        if not ser_data.is_valid():
            return Response({'message': 'در وارد کردن اطلاعات خود دقت کنید'}, status=status.HTTP_400_BAD_REQUEST)


        user_email = ser_data.validated_data.get('email')
        user = User.objects.filter(email__iexact=user_email).first()
        if user is None:
            return Response({'message': 'ایمیل وارد شده, قبلا ثبت نام نکرده است '},
                            status=status.HTTP_406_NOT_ACCEPTABLE)

        random_str = user.email_active_code
        msg = EmailMessage()
        msg['Subject'] = 'reset password account'
        msg['Form'] = EMAIL_HOST_USER
        msg['To'] = user_email
        msg.set_content(f'http://localhost:8000/account/reset-pass/{random_str}')
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT_SSL) as server:
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
            return Response(data=ser_data.data, status=status.HTTP_202_ACCEPTED)




class UserResetPasswordView(APIView):
    serializer_class = UserResetPasswordSerializer
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    """
    page reset password!
    """

    def post(self, request: HttpRequest, active_code):
        user: User = User.objects.filter(email_active_code__iexact=active_code).first()
        if user is None:
            return Response({'message': 'کاربری با همچنین ایمیلی ثبت نشده است'}, status=status.HTTP_404_NOT_FOUND)

        ser_data = UserResetPasswordSerializer(instance=user, data=request.POST)
        if not ser_data.is_valid():
            return Response({'message': 'در وارد کردن اطلاعات خود دقت کنید'}, status=status.HTTP_400_BAD_REQUEST)

        # ser_data.save() # این روش غیر امنیتی هست
        user_password = ser_data.validated_data.get('password')
        user.set_password(user_password)
        user.is_active = True
        user.email_active_code = get_random_string(84)
        user.save()
        return Response(data=ser_data.data, status=status.HTTP_202_ACCEPTED)


    # def put(self,request:HttpRequest):
    #     ser_date = UserRegisterSerializers(data=request.POST,partial=True)


class EditUserProfileView(APIView):
    serializer_class = EditUserProfileSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    permission_classes = [PermissionEditUserProfile, ]
    """
    this page for edit profile

    """

    def put(self, request: HttpRequest):
        current_user: User = User.objects.filter(id=request.user.id).first()
        self.check_object_permissions(request, current_user)
        ser_data = EditUserProfileSerializer(instance=current_user, data=request.POST, partial=True)
        if ser_data.is_valid():
            ser_data.save()
            return Response(data=ser_data.data, status=status.HTTP_206_PARTIAL_CONTENT)
        return Response(ser_data.errors, status=status.HTTP_409_CONFLICT)


class ChangePasswordAccountView(APIView):
    serializer_class = ChangePasswordAccoutSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    permission_classes = [PermissionEditUserProfile]

    """
    
    """

    def post(self, request: HttpRequest):
        user: User = User.objects.filter(id=request.user.id).first()
        ser_data = ChangePasswordAccoutSerializer(data=request.POST)
        if not ser_data.is_valid():
            return Response({'message': 'تداخل در انجام عملیات'}, status=status.HTTP_409_CONFLICT)

        current_password = ser_data.validated_data.get('current_password')
        new_password = ser_data.validated_data.get('new_password')
        if not user.check_password(current_password):
            return Response({'message': 'کلمه عبور اشتباه میباشد'}, status=status.HTTP_409_CONFLICT)

        print(current_password)
        print(new_password)
        user.set_password(new_password)
        user.save()
        return Response(data=ser_data.data, status=status.HTTP_202_ACCEPTED)


