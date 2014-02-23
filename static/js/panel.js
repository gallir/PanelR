var new_items = 0;

var data_timer = false;
var service_timer = false;
var min_update = 15000;
var next_update = 3000;
var xmlhttp;
var requests = 0;
var ping_time = 0;
var ping_start;
var total_requests = 0;
var max_requests = 2000;
var comment = '';
var last_comment_sent=0;
var comment_period = 5; //seconds
var ccnt = 0; 	// Connected counter

var play = true;

function start_panel() {
	$.ajaxSetup({timeout: 10000, async: true});

	$(document).ajaxError(function (request, settings) {
		data_timer = setTimeout('get_data()', next_update/2);
		xmlhttp = undefined;
	});
	do_play();
	return false;
}

function abort_request () {
	clearTimeout(data_timer);
	if ("object" == typeof(xmlhttp)) {
		xmlhttp.abort();
		xmlhttp = undefined;
	}
}

function get_data() {
	abort_request();
	var options = Object();
	options.k=mykey;
	options.ts=ts;
	options.v=my_version;
	options.r=total_requests;
	var date_object = new Date();
	ping_start = date_object.getTime();
	if(comment.length > 0) {
		options.text = comment;
		xmlhttp=$.post(panel_base_url, options, received_data);
		comment = '';
	} else {
		xmlhttp=$.get(panel_base_url, options, received_data);
	}
	requests++;
	total_requests++;
	return false;
}

function received_data(data) {
	xmlhttp = undefined;
	// Update ping time
	var date_object = new Date();
	if (ping_time == 0) 
		ping_time = date_object.getTime() - ping_start -15; // 15 ms is the smallest error in fastest machines
	else
		ping_time = parseInt(0.6 * ping_time + 0.4 * (date_object.getTime() - ping_start - 15)); // 15 ms also

	$('#ping').html(ping_time);

	var new_data = eval ('(' + data + ')');
	new_items= new_data.length;
	if(new_items > 0) {
		if (do_animation) clear_animation();
		next_update = Math.round(0.5*next_update + 0.5*min_update/(new_items*2));

		//Remove old items
		$('#panel-items').children().slice(max_items-new_items).remove();

		for (i=new_items-1; i>=0 ; i--) {
			if (new_data[i].ts > ts) ts = new_data[i].ts;
			html = $('<div class="panel-item">'+to_html(new_data[i])+'</div>');
			set_initial_display(html, i);
			$('#panel-items').prepend(html);
		}
		if (do_animation) {
			animation_timer = setInterval('animate_background()', 100);
			animating = true;
		}
	} else next_update = Math.round(next_update*1.05);
	if (next_update < 3000) next_update = 3000;
	if (next_update > min_update) next_update = min_update;
	if (requests > max_requests) {
		if ( !confirm('want to stay connected?') ) {
			return;
		}
		requests = 0;
		total_requests = 0;
		next_update = 100;
	}
	data_timer = setTimeout('get_data()', next_update);
}

function send_chat(form) {
	var currentTime = new Date();

	if(check_command(form.comment.value)) return false;

	if(!is_playing()) {
		alert("no playing");
		return false;
	}
	if(form.comment.value.length < 4) {
		alert("message too short");
		return false;
	}
	if( currentTime.getTime() < last_comment_sent + (comment_period*1000)) {
		alert("must wait " + comment_period + " seconds between messages");
		return false;
	}
	abort_request();
	comment=form.comment.value;
	last_comment_sent = currentTime.getTime();
	form.comment.value='';
	if (do_animation && animating) {
		data_timer = setTimeout('get_data()', 500)
	} else {
		get_data();
	}
	requests = 0;
	return false;
}

function check_command(comment) {
	if (!comment.match(/^!/)) return false;
	if (comment.match(/^!jefa/)) {
		window.location = 'telnet.php';
		return true;
	}
	if (comment.match(/^!fisgona/)) {
		window.location = 'panel.php';
		return true;
	}
	return false;
}


function is_playing () {
	return play;
}

function do_pause() {
	abort_request();
	clearInterval(service_timer);
	play = false;
}

function do_play() {
	play = true;
	get_data();
	if (do_check_service) {
		if ( service_timer) clearInterval(service_timer);
		check_service();
		service_timer = setInterval('check_service()', 30000);
	}
	
}

function check_service() {
	$.get(services_check_url, function (data) { if(data.length > 0) alert(data);});
}