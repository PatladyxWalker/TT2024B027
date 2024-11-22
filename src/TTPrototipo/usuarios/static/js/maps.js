document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('submitBtn').addEventListener('click', function(event) {
        event.preventDefault();

        const calle = document.getElementById('calle').value.trim();
        const numero = document.getElementById('NumExt').value.trim(); // Asegúrate de que el ID coincida con el HTML
        const cp = document.getElementById('CP').value.trim();
        const cpValidosGAM = [
            '07000', '07010', '07020', '07040', '07050', '07058', // Agrega todos los códigos postales válidos de GAM
            '07060', '07069', '07070', '07080', '07089', '07090',
            '07100', '07109', '07110', '07119', '07130', '07140',
            '07144', '07149', '07150', '07160', '07164', '07170',
            '07180', '07183', '07187', '07188', '07189', '07190',
            '07199', '07200', '07207', '07209', '07210', '07214',
            '07220', '07224', '07230', '07239', '07240', '07250',
            '07259', '07268', '07270', '07279', '07280', '07290',
            '07300', '07310', '07320', '07330', '07340', '07350',
            '07359', '07360', '07369', '07370', '07380', '07400',
            '07410', '07420', '07430', '07440', '07450', '07455',
            '07456', '07460', '07469', '07470', '07480', '07500',
            '07509', '07510', '07520', '07530', '07540', '07550',
            '07560', '07570', '07580', '07600', '07620', '07630',
            '07640', '07650', '07670', '07680', '07700', '07707',
            '07708', '07720', '07730', '07739', '07740', '07750',
            '07754', '07755', '07760', '07770', '07780', '07790',
            '07800', '07810', '07820', '07830', '07838', '07839',
            '07840', '07850', '07858', '07859', '07860', '07869',
            '07870', '07880', '07889', '07890', '07899', '07900',
            '07910', '07918', '07919', '07920', '07930', '07939',
            '07940', '07950', '07960', '07969', '07970', '07979',
            '07980', '07990'
        ];

        if (!cpValidosGAM.includes(cp)) {
            document.getElementById('mensajeError').innerText = "Solo se permite inmuebles en la GAM";
            return;
        } else {
            document.getElementById('mensajeError').innerText = "";
        }

        const direccionCompleta = `${calle} ${numero}, Ciudad de México, CP ${cp}`;
        mostrarMapa(direccionCompleta);
    });

    function mostrarMapa(direccion) {
        const mapaElemento = document.getElementById('mapa');

        // Verifica si el elemento `#mapa` es válido antes de usarlo.
        if (!mapaElemento) {
            console.error("El contenedor del mapa no se encontró en el DOM.");
            return;
        }

        const geocoder = new google.maps.Geocoder();
        const mapa = new google.maps.Map(mapaElemento, {
            zoom: 16,
            center: { lat: 19.432608, lng: -99.133209 } // Centro de CDMX
        });

        geocoder.geocode({ 'address': direccion }, function(results, status) {
            if (status === 'OK') {
                mapa.setCenter(results[0].geometry.location);
                new google.maps.Marker({
                    map: mapa,
                    position: results[0].geometry.location
                });
            } else {
                alert('No se pudo mostrar la dirección: ' + status);
            }
        });
    }
});

