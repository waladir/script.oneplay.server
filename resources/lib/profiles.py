# -*- coding: utf-8 -*-
# SHARED: Oneplay Server, TVheadend
from resources.lib.api import API
from resources.lib.utils import get_config_value


def get_profile_id(session, reset=False):
    """Vrátí ID nastaveného, případně prvního dostupného profilu."""
    data = API().user_profiles_display(session=session) or {}
    selected_profile = get_config_value('profile')
    first_profile_id = None
    available_profiles = data.get('availableProfiles') or {}
    for profile in available_profiles.get('profiles') or []:
        profile = profile.get('profile') or {}
        if first_profile_id is None:
            first_profile_id = profile.get('id')
        if profile.get('name') == selected_profile or not selected_profile:
            return profile.get('id')
    return first_profile_id
