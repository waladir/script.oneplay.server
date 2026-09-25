# -*- coding: utf-8 -*-
# SHARED: Oneplay Server, TVheadend
from resources.lib.api import API
from resources.lib.utils import get_config_value, log_message


def get_profile_id(session):
    """Vrátí ID nastaveného, případně prvního dostupného profilu."""
    data = API().user_profiles_display(session=session) or {}
    selected_profile = get_config_value('profile')
    first_profile_id = None
    selected_id = None    
    available_profiles = data.get('availableProfiles') or {}
    profiles = available_profiles.get('profiles') or []
    for profile in profiles:
        profile = profile.get('profile') or {}
        if first_profile_id is None:
            first_profile_id = profile.get('id')
        if selected_id is None and (profile.get('name') == selected_profile or not selected_profile):
            selected_id = profile.get('id')
    result_id = selected_id or first_profile_id
    if get_config_value('debug') in (1, '1', -1, '-1', 'true'):
        log_message('Oneplay > Dostupné profily: ' + ', '.join((item.get('profile') or {}).get('name', 'Unknown') + (' [POUŽITÝ]' if (item.get('profile') or {}).get('id') == result_id else '') for item in profiles))
    return result_id
