$(document).ready(function() {
    console.log("peepee");
    var table = $('#similarPlaylists').DataTable( {
        dom: 'Bfrtip',
        select: true,
        search: false,
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