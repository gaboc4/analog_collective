$(function () {
    $('[data-toggle="tooltip"]').tooltip()
  })

$(document).ready(function() {
    console.log("peepee");
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
