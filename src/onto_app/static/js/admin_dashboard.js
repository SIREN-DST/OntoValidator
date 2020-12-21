$(function() {
    $('#upload-ontology-btn').on('change', function() {
        var form_data = new FormData($('#upload-ontology')[0]);
        $.ajax({
            type: 'POST',
            url: '/upload_ontology',
            data: form_data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(data) {
                document.write(data);
            },
        });
    });
});

$('.close-icon').on('click',function() {
  $(this).closest('.card').fadeOut();
  var ont_dict = {"name": $(this).attr('name')};
  $.ajax({
        type: 'POST',
        url: '/delete_ontology',
        data: JSON.stringify(ont_dict),
        contentType: "application/json",
        cache: false,
        processData: false,
        success: function(data) {
            console.log(data["Message"]);
        },
    });
})