$(function () {
    $('[data-toggle="tooltip"]').tooltip()
  })

$(document).ready(function() {

  var existingSongsTable = $('#existingSongs').DataTable( {
      dom: 'Bfrtip',
      select: {
        style: 'single'
      },
      paging: false,
      searching: false,
      buttons: [{text: "", className: 'existingSongsBtn'}]
  } );

  var table = $('#similarPlaylists').DataTable( {
      dom: 'Bfrtip',
      select: {
        style: 'single'
      },
      paging: false,
      searching: false,
      buttons: [
          {
              text: 'Add song to playlist',
              action: function () {
                  console.log(table.rows( { selected: true } ).data()[0][0]);
                  regex = new RegExp(/<([^\s]+).*?id="([^"]*?)".*?>(.+?)<\/\1>/gi);
									matches = existingSongsTable.rows({ selected: true}).data()[0][1].match(regex);
									results = [];
									for (i in matches) {
									    parts = regex.exec(matches[i]);
									    results.push(parts[2])
									}

                  if (confirm("Are you sure you want to add your song to this playlist?")) {
                    route = '/song_to_plist?plist_id=' + table.rows( { selected: true } ).data()[0][0] +
                            '&song_id=' + results[0]
                    fetch(route, {
						          method: 'POST'
						        }).then(function(result) {
						          return result.json()
						        }).then(redirectAfterPlistAdd);
                  } else {
                    alert("Addition cancelled");
                  }

              }
          }
      ]
  } );

  function redirectAfterPlistAdd(responseJson) {
    if (responseJson.error) {
			alert("Error adding song to playlist, please try again");
    }
    else {
      window.location.href = "/artist_profile"
    }
  }




  table.column( 0 ).visible( false );

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
        creditAmount = document.getElementById('credit-amount').value;
        if (creditAmount == 10) {price = 6000}
        else if (creditAmount == 50) {price = 25000}
        else if (creditAmount == 100) {price = 45000}
        else {return alert("Please make sure you enter one of the valid credit options from the table");}
        fetch('/shop/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payment_method_id: result.paymentMethod.id ,
                                  price: price, new_credits: creditAmount})
        }).then(function(result) {
          return result.json();
        }).then(handleServerResponse);
      }
    }

    function handleServerResponse(responseJson) {
      if (responseJson.error) {
        // An error happened when charging the card, show it in the payment form
        alert("Error processing payment, please try again");
      } else {
        // Show a success message
        $('#purchaseCard').append( "<p>Thank you! You will be redirected to your profile in a moment</p>" );
        window.location.href = "/artist_profile";
      }
    }
  }
});
