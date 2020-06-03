from django import forms
from django.contrib.auth.forms import UserCreationForm
#from django.contrib.auth import get_user_model
from .models import MyUser, DeliveryAddress

#User = get_user_model()


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length = 32, required = True, widget=forms.TextInput(attrs={'class':'form-control' , 'autocomplete': 'off','pattern':'[A-Za-z ]+', 'title':'Enter Characters Only '}))
    last_name = forms.CharField(max_length = 32, required = True, widget=forms.TextInput(attrs={'class':'form-control' , 'autocomplete': 'off','pattern':'[A-Za-z ]+', 'title':'Enter Characters Only '}))
    email = forms.EmailField(max_length = 256, required = True)

    delivery_address_x_coord = forms.IntegerField(label = "X Coordinate of Delivery Address")
    delivery_address_y_coord = forms.IntegerField(label = "Y Coordinate of Delivery Address")
   
    class Meta(UserCreationForm.Meta):
        model = MyUser
        fields = ['username', 'first_name', 'last_name',  'email', 'password1', 'password2', 'delivery_address_x_coord', 'delivery_address_y_coord']

    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        delivery_address = DeliveryAddress.objects.create()
        delivery_address.x = self.cleaned_data['delivery_address_x_coord']
        delivery_address.y = self.cleaned_data['delivery_address_y_coord']
        delivery_address.save()
        user.delivery_address = delivery_address

        if commit:
            user.save()
        return user



class ProductSearchForm(forms.Form):
    product_type = forms.ChoiceField(label="", choices=[("apple", "apple"), ("orange", "orange"), ("banana", "banana"), ("strawberry", "strawberry"), ("pineapple", "pineapple")])



class ProductAmountForm(forms.Form):
    product_amount = forms.IntegerField(label="Product Amount", max_value=999, min_value=1)



class DeliveryAddressForm(forms.Form):
    x = forms.IntegerField(label="X Coordinate")
    y = forms.IntegerField(label="Y Coordinate")