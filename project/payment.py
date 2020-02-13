from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from .models import Users
from . import db
import os
import stripe
import json

payment = Blueprint('payment', __name__)

stripe.api_key = os.environ['STRIPE_KEY']


@payment.route('/shop/', methods=['GET', 'POST'])
@login_required
def submit_payment():
    user = Users.query.filter_by(email=current_user.email).first()
    curr_credits = user.credits if user.credits is not None else 0
    if request.method == 'GET':
        return render_template('shop.html',
                               tokens=curr_credits, error='',
                               user_name=user.first_name + " " + user.last_name)
    elif request.method == "POST":
        data = request.get_json()
        try:
            # Create the PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=data['price'],
                currency='usd',
                payment_method=data['payment_method_id'],
                confirm=True,
                error_on_requires_action=True,
            )
            return generate_response(intent, data['new_credits'])
        except stripe.error.CardError as e:
            return json.dumps({'error': e.user_message}), 200


def generate_response(intent,new_credits):
    if intent.status == 'succeeded':
        user = Users.query.filter_by(email=current_user.email).first()
        user.credits += int(new_credits)
        db.session.commit()
        return json.dumps({'sucess': True}), 200
    else:
        # Any other status would be unexpected, so error
        return json.dumps({'error': 'Invalid PaymentIntent status'}), 500
