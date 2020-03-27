from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Users
from . import db
import os
import stripe
import json

payment = Blueprint('payment', __name__)

stripe.api_key = os.environ['STRIPE_KEY']


@payment.route('/shop')
@login_required
def shop():
    user = Users.query.filter_by(email=current_user.email).first()
    curr_credits = user.credits if user.credits is not None else 0
    # if user.payment_info is None:
    #     customer = stripe.Customer.create(
    #         email=user.email
    #     )
    #     intent = stripe.SetupIntent.create(
    #         customer=customer['id'],
    #         payment_method_types=["card"]
    #     )
    #     user.payment_info = customer['id']
    #     db.session.commit()
    #     print(intent.client_secret)
    #     return render_template('shop.html', payment_info=0, client_secret=intent.client_secret,
    #                            tokens=curr_credits, user_name=user.first_name + " " + user.last_name)
    return render_template('shop.html',
                           tokens=curr_credits, user_name=user.first_name + " " + user.last_name)


@payment.route('/payment_form', methods=['POST'])
@login_required
def purchase_tokens():
    user = Users.query.filter_by(email=current_user.email).first()
    new_credits = request.form.get('credit-amount')
    user.credits += int(new_credits)
    db.session.commit()
    return redirect(url_for('payment.shop'))
