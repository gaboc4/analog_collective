$(function () {
    $('[data-toggle="tooltip"]').tooltip()
  })

$(document).ready(function() {
    var table = $('#similarPlaylists').DataTable( {
        dom: 'Bfrtip',
        select: {
          style: 'single'
        },
        paging: false,
        searching: false,
        buttons: [
            {
                text: 'Get selected data',
                action: function () {
                    console.log(table.rows( { selected: true } ).data());
                }
            }
        ]
    } );
} );

// $(document).ready(function() {
//     var table = $('#tokenOptions').DataTable( {
//         dom: 'Bfrtip',
//         select: {
//           style: 'single'
//         },
//         paging: false,
//         searching: false,
//         buttons: [
//             {
//                 text: 'Add tokens to account',
//                 action: function () {
//                     console.log(table.rows( { selected: true } ).data());
//                 }
//             }
//         ]
//     } );
// } );

$(document).ready(function() {
  if ($(".shopPage")[0]) {
    var stripe = Stripe('pk_test_jdpZ0e0VuV3QPYHePcK21chZ0033T1alyY');

    var elements = stripe.elements();
    var cardElement = elements.create('card');
    cardElement.mount('#card-element');

    var cardholderName = document.getElementById('cardholder-name');
    var form = document.getElementById('payment-form');

    var resultContainer = document.getElementById('payment-result');
    cardElement.addEventListener('change', function(event) {
      if (event.error) {
        resultContainer.textContent = event.error.message;
      } else {
        resultContainer.textContent = '';
      }
    });

    form.addEventListener('submit', function(event) {
      event.preventDefault();
      resultContainer.textContent = "";
      stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
        billing_details: {name: cardholderName.value}
      }).then(handlePaymentMethodResult);
    });

    function handlePaymentMethodResult(result) {
      if (result.error) {
        // An error happened when collecting card details, show it in the payment form
        resultContainer.textContent = result.error.message;
      } else {
        // Otherwise send paymentMethod.id to your server (see Step 3)
        fetch('/shop/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payment_method_id: result.paymentMethod.id ,
                                  price: document.getElementById('token-amount').value * 10})
        }).then(function(result) {
          return result.json();
        }).then(handleServerResponse);
      }
    }

    function handleServerResponse(responseJson) {
      if (responseJson.error) {
        // An error happened when charging the card, show it in the payment form
        window.location.href = "/artist_profile";
      } else {
        // Show a success message
        window.location.href = "/artist_profile";
      }
    }
  }
});
