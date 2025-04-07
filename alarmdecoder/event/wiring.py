# alarmdecoder/event/wiring.py

def wire_events(decoder):
    decoder.on_open += decoder._on_open
    decoder.on_close += decoder._on_close
    decoder.on_read += decoder._on_read
    decoder.on_write += decoder._on_write
    decoder.on_zone_fault += decoder._on_zone_fault
    decoder.on_zone_restore += decoder._on_zone_restore
    decoder.on_message += decoder._update_internal_states
    decoder.on_expander_message += decoder.update_expander_status
    decoder.on_rfx_message += decoder._update_zone_tracker
    decoder.on_lrr_message += decoder._update_zone_tracker
    decoder.on_aui_message += decoder._update_zone_tracker
    decoder.on_panic += decoder._on_panic
    decoder.on_relay_changed += decoder._on_relay_changed
    decoder.on_chime_changed += decoder._on_chime_changed
    decoder.on_bypass += decoder._on_bypass
    decoder.on_alarm += decoder._on_alarm
    decoder.on_alarm_restored += decoder._on_alarm_restored
    decoder.on_fire += decoder._on_fire
    decoder.on_bypass += decoder._on_bypass
    decoder.on_alarm_restored += decoder._on_alarm_restored
    decoder.on_alarm += decoder._on_alarm
    decoder.on_config_received += decoder._on_config_received
    decoder.on_alarm_restored += decoder._on_alarm_restored
    decoder.on_alarm += decoder._on_alarm
    decoder.on_arm += decoder._on_arm
    decoder.on_disarm += decoder._on_disarm
    decoder.on_ready_changed += decoder._on_ready_changed
    decoder.on_power_changed += decoder._on_power_changed


def unwire_events(decoder):
    decoder.on_open -= decoder._on_open
    decoder.on_close -= decoder._on_close
    decoder.on_read -= decoder._on_read
    decoder.on_write -= decoder._on_write
    decoder.on_zone_fault -= decoder._on_zone_fault
    decoder.on_zone_restore -= decoder._on_zone_restore
    decoder.on_message -= decoder._update_internal_states
    decoder.on_expander_message -= decoder._update_expander_status
    decoder.on_rfx_message -= decoder._update_zone_tracker
    decoder.on_lrr_message -= decoder._update_zone_tracker
    decoder.on_aui_message -= decoder._update_zone_tracker
    decoder.on_panic -= decoder._on_panic
    decoder.on_relay_changed -= decoder._on_relay_changed
    decoder.on_chime_changed -= decoder._on_chime_changed
    decoder.on_bypass -= decoder._on_bypass
    decoder.on_alarm -= decoder._on_alarm
    decoder.on_alarm_restored -= decoder._on_alarm_restored
    decoder.on_fire -= decoder._on_fire
    decoder.on_bypass -= decoder._on_bypass
    decoder.on_alarm_restored -= decoder._on_alarm_restored
    decoder.on_alarm -= decoder._on_alarm
    decoder.on_config_received -= decoder._on_config_received
    decoder.on_alarm_restored -= decoder._on_alarm_restored
    decoder.on_alarm -= decoder._on_alarm
    decoder.on_arm -= decoder._on_arm
    decoder.on_disarm -= decoder._on_disarm
    decoder.on_ready_changed -= decoder._on_ready_changed
    decoder.on_power_changed -= decoder._on_power_changed




