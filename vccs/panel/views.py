import re

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.db.models import Q

from .models import BottomUp, ControllerPositions
import panel.vatsim_data as vatsim_data

from loguru import logger

VATSIM_DATA = vatsim_data.Vatsim()

def vatsim_status(request):
    """only accept connections from localhost"""
    # get client ip address
    client_ip = request.scope["client"]
    if client_ip[0] == "127.0.0.1":
        logger.debug(client_ip[0])
        json_response = VATSIM_DATA.url_get_json(VATSIM_DATA.v3_url)
        logger.trace(json_response)

        return JsonResponse(json_response)
    return PermissionDenied

def vccs_main_panel(request, aerodrome_icao=None):
    """
    Redirect the user to VATSIM SSO if no token found
    """

    # check if user is logged in (is there a valid session cookie)
    try:
        user_data = request.session["data"]
        logger.success("User data found")
        logger.trace(user_data)
    except KeyError:
        logger.info("OAuth Redirect")
        return redirect("/oauth/login/")
    
    # check if user is logged into an atc position
    all_active_controllers = VATSIM_DATA.get_controller()
    try:
        check_callsign = VATSIM_DATA.get_controller(int(user_data["cid"]))
        logger.success("CID '{}' and callsign '{}' match the logged in list on VATSIM", user_data["cid"], check_callsign)
    except IndexError:
        check_callsign = f"OBSERVER-{user_data['cid']}"
    
    # get all aerodromes if none selected or if user is OBSERVER
    if aerodrome_icao is None:
        logger.debug("Listing all positions")
        all_entries = ControllerPositions.objects.order_by('prefix', 'suffix').all()
    else:
        # get the list of controllers who provide top down coverage for this aerodrome
        ai_list = []
        try:
            airspace_inheritance = BottomUp.objects.get(aerodrome__exact=str(aerodrome_icao).upper())
            logger.info("Airspace inheritance above APP is {}", str(airspace_inheritance.airspace_inheritance))
            # turn the returned string into a list
            ai_split = str(airspace_inheritance.airspace_inheritance).split("|")
            for callsign in ai_split:
                ai_list.append(callsign)
        except BottomUp.DoesNotExist:
            pass
        logger.debug("Listing positions for {}", str(aerodrome_icao).upper())
        aerodrome_regex = r'^' + re.escape(str(aerodrome_icao).upper()) + r'\_'
        all_entries = ControllerPositions.objects.order_by("prefix", "middle_letter", "suffix", "identifier").filter(Q(name_of_position__regex=aerodrome_regex) | Q(name_of_position__in=ai_list))
    
    output = []
    filter_list = set()
    start = True
    for entry in all_entries:
        # narrow down to UK positions only
        if re.match(r"^(EG[A-Z]{2}\_|LON\_|LTC\_|SCO\_|MAN\_|ESSEX\_|THAMES\_|SOLENT\_)", entry.name_of_position):
            if start:
                aerodrome = re.search(r"^(EG[A-Z]{2}|LON|LTC|SCO|MAN|ESSEX|THAMES|SOLENT)", entry.prefix)
                aerodrome = aerodrome.group(1)
                output.append(f'<div class="col"><div class="btn-group-vertical">')
                start = False
            filter_list.add(aerodrome)
            
            # get the last two characters from the aerodrome ICAO
            if re.match(r"^EG[A-Z]{2}\_", entry.name_of_position):
                sub_fix = f"{entry.name_of_position[2]}{entry.name_of_position[3]}"
            else:
                sub_fix = entry.name_of_position

            # set some pretty button colours (possibly update with js)
            logger.trace("Position {}, Callsign {}", entry.name_of_position, check_callsign)
            if entry.name_of_position == check_callsign:
                colour = "light disabled"
            elif (entry.name_of_position in all_active_controllers) or (str(entry.name_of_position).replace("_", "__") in all_active_controllers):
                # includes check for relief callsigns with _ _ instead of _
                colour = "warning disabled"
            else:
                colour = "secondary disabled"

            
            button_start = f'<button type="button" class="btn btn-{colour} btn-group-lg border static-button-width" data-toggle="tooltip" data-placement="top"'
            button_end = f'{button_start} id="status{entry.name_of_position}" title="{entry.radio_callsign}\n{entry.name_of_position}" onclick="call(\'{entry.name_of_position}\')" disabled>{sub_fix}<br/>{entry.suffix}<br/>{entry.frequency}</button>'
            # process everything except ATIS callsigns
            if (entry.prefix == aerodrome) and ("ATIS" not in entry.suffix) and ("FSS" not in entry.suffix):
                output.append(button_end)
            elif ("ATIS" not in entry.suffix) and ("FSS" not in entry.suffix):
                output.append('</div></div>')
                output.append('<div class="col"><div class="btn-group-vertical">')
                output.append(button_end)

            aerodrome = re.search(r"^(EG[A-Z]{2}|LON|LTC|SCO|MAN|ESSEX|THAMES|SOLENT)", entry.prefix)
            aerodrome = aerodrome.group(1)
    output.append('</div></div>')

    # vars to send to the template renderer    
    context = {
        "cid": user_data["cid"],
        "full_name": user_data["personal"]["name_full"],
        "callsign": check_callsign,
        "positions": output,
        "pos_filter": sorted(filter_list),
    }
    template = loader.get_template('vccs.html')

    return HttpResponse(template.render(context, request))
