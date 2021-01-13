<template id="template">
    <div class="card">
        <div class="card-content">
            <span class="card-title"> Simulation Map </span>

            <div id="map" class="google_map" style="height: 800px;">
            </div>
        </div>
    </div>
</template>

<script>
    module.exports = {
        name: "SimulationGoogleMap",
        template:"#template",
        props:["config", "simulation"],
        data(){
            return{
                map:{},
                map_bounds:{},
                map_rectangle:null,
                map_zoom:null,
                settings:{
                    size:[]
                },
                center_lat:0,
                center_long:0,
                rectangles:[],
                cookie: this.getCookie('swarm_southampton_cookie'),
            }
        },
        methods:{
            async sleep(ms) {
              return new Promise(resolve => setTimeout(resolve, ms));
            },

            // get data

            async GET(url, timeout, nr_tries){
                let checked = false;
                let current_tries = 0;
                let data = {};

                while( !checked && current_tries < nr_tries) {
                    await fetch(url)
                        .then(response => response.json())
                        .then(json_parsed => {
                            if( (json_parsed instanceof Array && json_parsed.length > 0) ||
                                (json_parsed instanceof Object && Object.keys(json_parsed).length > 0) ){
                                    data = json_parsed;
                                    checked = true;
                            }

                        })
                        .catch(err => {
                            console.log('Request Failed', err);
                        });

                    if(!checked) {
                        await this.sleep(timeout);
                        current_tries++;
                    }
                }

                return data;
            },

            // get user cookie
            getCookie(cookie){
                const value = `; ${document.cookie}`;
                const parts = value.split(`; ${cookie}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
            },

            // send data
            SEND( data, url ){
                var xhr = new XMLHttpRequest();
                xhr.open("POST", url, true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send(JSON.stringify(data));
            },

            // send operator action
            send_operator_action(action_name, row, col){
                let json_data = {
                    "action": action_name,
                    "pos": [row, col],
                };

                this.SEND( json_data, `/api/v1/simulations/${this.simulation.id}/add_action/` );
            },

            // send statistics data
            send_behaviour(action_name){
                let json_data = {
                    "action": action_name,
                    "time": new Date(),
                    "timestep": 0, // need to implement once we finish integrating and revamping the play function
                    "simulation_id": this.simulation.id,
                    "cookie": this.cookie
                };

                this.SEND(json_data, `/api/v1/simulations/${this.simulation.id}/records/`)
            },

            // setup
            async importMap(){
                let url = 'http://localhost:8000/static/js/google_maps/Map.js';
                const {MAP} = await import(url);
                this.map = new MAP(this.center_lat, this.center_long, 14);
                this.map.init_map();
                this.map_zoom = this.map.map.getZoom();

                this.add_rectangle();
                this.createInitialGrid(null);
                this.add_listeners();

                await this.play();
            },

            add_rectangle(){
                const rectangle = new google.maps.Rectangle({
                    strokeColor: "#ffffff",
                    strokeOpacity: 0.8,
                    strokeWeight: 2,
                    fillColor: "#ffffff",
                    fillOpacity: 0.35,
                    map:this.map.map,
                    bounds: this.map_bounds,
                });
                this.map_rectangle = rectangle;
            },

            add_listeners(){
                this.map.map.addListener("dragend", () => {
                    this.send_behaviour("dragged");
                });

                this.map.map.addListener("zoom_changed", () => {
                    if( this.map_zoom < this.map.map.getZoom() ){
                        this.send_behaviour("zoom_in");
                    }else{
                        this.send_behaviour("zoom_out");
                    }
                    this.map_zoom = this.map.map.getZoom();
                });

            },

            // map processing

            createInitialGrid(confidence) {
                let app = this;
                let left_dist = Math.abs(this.map_rectangle.getBounds().getNorthEast().lng() - this.map_rectangle.getBounds().getSouthWest().lng());
                let below_dist = Math.abs(this.map_rectangle.getBounds().getNorthEast().lat() - this.map_rectangle.getBounds().getSouthWest().lat());

                let sq_lat = below_dist / this.settings.size[0];
                let sq_long = left_dist / this.settings.size[1];

                for (var i = 0; i < this.settings.size[0]; i++) {
                    let map_col = [];

                    for (var j = 0; j < this.settings.size[1]; j++) {
                        const row = i;
                        const col = j;

                        let top_lat = this.map_rectangle.getBounds().getNorthEast().lat() - (sq_lat * i);
                        let btm_lat = this.map_rectangle.getBounds().getNorthEast().lat() - (sq_lat * (i + 1));

                        let left_lng = this.map_rectangle.getBounds().getSouthWest().lng() + (sq_long * j);
                        let right_lng = this.map_rectangle.getBounds().getSouthWest().lng() + (sq_long * (j + 1));

                        if (confidence === null)
                            overlay = 0;
                        else
                            overlay = 1 - confidence[i][j];

                        let rectangle = new google.maps.Rectangle({
                            strokeColor: '#FFFFFF',
                            strokeOpacity: 0,
                            strokeWeight: 2,
                            fillColor: '#FFFFFF',
                            fillOpacity: overlay,
                            map: app.map.map,
                            bounds: new google.maps.LatLngBounds(
                                new google.maps.LatLng(top_lat, left_lng),
                                new google.maps.LatLng(btm_lat, right_lng)
                            ),
                        });

                        rectangle.addListener("click", () => {
                            this.send_operator_action("attract", row, col);
                        });

                        rectangle.addListener("rightclick", () => {
                            this.send_operator_action("deflect", row, col);

                        });

                        map_col.push({
                            "overlay": rectangle,
                            "marker_pos": rectangle.getBounds().getCenter()
                        });
                    }

                    this.rectangles.push(map_col);
                }
            },

            draw_confidence(confidence){
                if( this.rectangles.length === 0 ){
                    this.createInitialGrid(confidence);
                }else{
                    this.rectangles.forEach( (rectangles_row, row) => {
                        rectangles_row.forEach( (rectangle, col) => {
                            let new_opac = 1 - confidence[row][col];
                            rectangle.overlay.fillOpacity = new_opac;
                            rectangle.overlay.fillColor = "white";
                            rectangle.overlay.setOptions({fillOpacity: new_opac });
                        });
                    });
                }
            },

            draw_disasters(disasters){
                disasters.forEach((disaster) => {
                    let coords = this.rectangles[disaster[0]][disaster[1]].marker_pos;
                    this.rectangles[disaster[0]][disaster[1]].overlay.fillColor = "red";
                    this.rectangles[disaster[0]][disaster[1]].overlay.fillOpacity = 1;
                });
            },

            // main method

            async play(){
                let req;

                for( var i = 1; i <= 1000; i++ ){
                    req = await this.GET(`/api/v1/simulations/${this.simulation.id}/timestep/${i}`, 1000, 10);

                    if( req[0] !== undefined ) {
                        let data = JSON.parse(req[0].config.replaceAll("\'", "\""));

                        let disasters = data.belief;
                        let confidence = data.confidence;

                        this.draw_confidence(confidence);django_content_type
                        this.draw_disasters(disasters);
                    }
                }
            }
        },
        mounted(){
            this.map_bounds.north = this.config.NE.lat;
            this.map_bounds.south = this.config.SW.lat;
            this.map_bounds.east = this.config.NE.long;
            this.map_bounds.west = this.config.SW.long;

            this.center_lat = (this.map_bounds.north + this.map_bounds.south) / 2;
            this.center_long = (this.map_bounds.east + this.map_bounds.west) / 2;

            this.settings.size = [this.simulation.width, this.simulation.height];

            this.importMap();
        }
    }
</script>