from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.decorators import detail_route, list_route
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle
from clients.serializers.userAuth import (AuthenticateCredentialsSerializer, AuthenticateTokenSerializer, PasswordChangeSerializer, 
                                          RequestPasswordRecoverySerializer, TokenPasswordChangeSerializer)

from clients.auth import userAuth
from logic.exceptions import APIException, AuthenticationFailed, PermissionDenied, ExceptionCodes
from logic.auth import authenticateUser, createUserJWT, validateUserJWT, getUserPasswordValidatorMessages

#about docstrings yaml: http://django-rest-swagger.readthedocs.org/en/latest/yaml.html#parameters

#Throttle for non authenticated users, restrictive
class NonAuthThrottle(SimpleRateThrottle):
    rate = '5/min'
    scope = 'nonauth'

    def get_cache_key(self, request, view):
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

    #Do not inform throttling time on auth
    def wait(self):
        return None

#Less restrictive auth throttle
class AuthThrottle(SimpleRateThrottle):
    rate = '10/min'
    scope = 'auth'

    def get_cache_key(self, request, view):
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }

    #Do not inform throttling time on auth
    def wait(self):
        return None

class UserAuth(viewsets.ViewSet):
    '''
        User Authentication public API.<br/>
        _____________________________________________________________<br/>
    '''
  
    def _getUserData(self, user, token):

        return {
                'id':user.pk,     
                'email':user.email,
                'firstName':user.firstName,
                'lastName':user.lastName,
                'token':token
            }
        

    @list_route(methods=['post'], throttle_classes = (NonAuthThrottle,))
    def authenticate(self, request):           #Method name all lower case to be able to work correctly with docs
        '''
            Authenticates user credentials and returns an authentication token and data.
            Inactive users will fail to authenticate.<BR/>
            
            ---
            request_serializer: AuthenticateCredentialsSerializer
            
            responseMessages:
                - code: 403
                  message: permissionError
                - code: 400
                  message: validationError
                - code: 429
                  message: throttled
            
        '''      
        data = AuthenticateCredentialsSerializer(data=request.data)
        data.is_valid(True) 
        
        user = authenticateUser(
            data.validated_data['email'],
            data.validated_data['password'],
            True,
            True,
            PermissionDenied
        )

        token = createUserJWT(user)
                
        return Response(self._getUserData(user, token))


    @list_route(methods=['post'])
    def authenticatetoken(self, request):           #Method name all lower case to be able to work correctly with docs
        '''
            Authenticates user token.
            Inactive users will fail to authenticate
            
            ---
            request_serializer: AuthenticateTokenSerializer
                       
            responseMessages:
                - code: 403
                  message: permissionError, requiresPasswordChange
                - code: 400
                  message: validationError
                
            
        '''      
        data = AuthenticateTokenSerializer(data=request.data)
        data.is_valid(True)   
        
        user, tokenData = validateUserJWT(data.validated_data['token'], True, PermissionDenied)
                               
        return Response(self._getUserData(user, data.validated_data['token']) )


    #This one requires an already authenticated user.
    @list_route(methods=['post'], authentication_classes=(userAuth.JWTUserAuthenticator,), permission_classes = (IsAuthenticated,), throttle_classes = (AuthThrottle,))
    def changepassword(self, request): 
        '''
            Changes current authenticated user password. Returns an updated token to prevent session expiration.
            
            ---
            request_serializer: PasswordChangeSerializer
            
            responseMessages:
                - code: 401
                  message: authenticationError
                - code: 400
                  message: validationError
                
            
        '''      
        data = PasswordChangeSerializer(data=request.data, context={'user':request.user})
        data.is_valid(True)   
               
        user = data.save()
        token = createUserJWT(user)
                
        return Response(token)

    
    @list_route(methods=['get'])
    def passwordpolicy(self, request): 
        '''
            Returns a list of password requirements.
        '''

        return Response(getUserPasswordValidatorMessages())


    @list_route(methods=['post'], throttle_classes = (NonAuthThrottle,))
    def requestpasswordrecovery(self, request): 
        '''
            Requests a password recovery for the given user email.
            
            ---
            request_serializer: RequestPasswordRecoverySerializer
            
            responseMessages:
                - code: 400
                  message: validationError
                
            
        '''      
        data = RequestPasswordRecoverySerializer(data=request.data)
        data.is_valid(True)   
               
        data.save()
                
        return Response()


    @list_route(methods=['post'], throttle_classes = (AuthThrottle,))
    def tokenchangepassword(self, request): 
        '''
            Updates a user password given a token and new password
            
            ---
            request_serializer: TokenPasswordChangeSerializer
            
            responseMessages:
                - code: 403
                  message: permissionError
                - code: 400
                  message: validationError
                
            
        '''      
        data = TokenPasswordChangeSerializer(data=request.data)
        data.is_valid(True)   
               
        data.save()
                
        return Response()