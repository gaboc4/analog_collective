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

	var stripe =  Stripe(env.STRIPE_PK);
	var elements = stripe.elements();
	var cardElement = elements.create('card');
	cardElement.mount('#card-element');

	var cardholderName = document.getElementById('cardholderName');
	var cardButton = document.getElementById('card-button');
	var clientSecret = cardButton.dataset.secret;

	cardButton.addEventListener('click', function(ev) {
	  stripe.confirmCardSetup(
	    clientSecret,
	    {
	      payment_method: {
	        card: cardElement,
	        billing_details: {
	          name: cardholderName.value,
	        },
	      },
	    }
	  ).then(function(result) {
	    if (result.error) {
          changeLoadingState(false);
          var displayError = document.getElementById("card-errors");
          displayError.textContent = result.error.message;
	    } else {
	      orderComplete(stripe, clientSecret);
	    }
	  });
	});


	/* Shows a success / error message when the payment is complete */
	var orderComplete = function(stripe, clientSecret) {
	  stripe.retrieveSetupIntent(clientSecret).then(function(result) {
	    var setupIntent = result.setupIntent;
	    var setupIntentJson = JSON.stringify(setupIntent, null, 2);

	    document.querySelector(".sr-payment-form").classList.add("hidden");
	    document.querySelector(".sr-result").classList.remove("hidden");
	    document.querySelector("pre").textContent = setupIntentJson;
	    setTimeout(function() {
	      document.querySelector(".sr-result").classList.add("expand");
	    }, 200);

	    changeLoadingState(false);
	  });
	};

	var changeLoadingState = function(isLoading) {
  if (isLoading) {
    document.querySelector("button").disabled = true;
    document.querySelector("#spinner").classList.remove("hidden");
    document.querySelector("#button-text").classList.add("hidden");
  } else {
    document.querySelector("button").disabled = false;
    document.querySelector("#spinner").classList.add("hidden");
    document.querySelector("#button-text").classList.remove("hidden");
  }
};




});
