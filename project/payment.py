from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Users
from . import db
import os
import stripe
import json

payment = Blueprint('payment', __name__)


stripe.api_key = os.environ['STRIPE_SK']


@payment.route('/shop')
@login_required
def shop():
    user = Users.query.filter_by(email=current_user.email).first()
    curr_credits = user.credits if user.credits is not None else 0

    return render_template('shop.html', key=os.environ['STRIPE_PK'],
                           tokens=curr_credits, user_name=user.first_name + " " + user.last_name)


@payment.route('/payment_form', methods=['POST'])
@login_required
def purchase_tokens():
    user = Users.query.filter_by(email=current_user.email).first()
    try:
        new_credits = request.form.get('credit-amount')
        user.credits += int(new_credits)

        if user.payment_info is None:
            customer = stripe.Customer.create(
                email=current_user.email,
                source=request.form['stripeToken']
            )
            user.payment_info = customer.id
            db.session.commit()

        stripe.Charge.create(
            customer=user.payment_info,
            amount=int(new_credits)*500,
            currency='usd',
            description="Analog Collective token purchase for {} credits".format(str(new_credits))
        )

        flash('Payment success!')
        return redirect(url_for('payment.shop'))
    except stripe.error.StripeError as e:
        print(e)
        flash('Something went wrong when processing your payment, please try again.')
        return redirect(url_for('payment.shop'))
