"""
Polls Emporia Vue for current home energy + EV charger usage via the
unofficial pyemvue library, and writes the result to emporia-data.json
at the repo root — the dashboard fetches that file directly as a
same-origin static file, no live API call needed at page-load time.

Credentials come from environment variables (set as GitHub Secrets in
the workflow, never hardcoded here).
"""
import os
import sys
import json
import datetime

from pyemvue import PyEmVue
from pyemvue.enums import Scale, Unit


def main():
    email = os.environ.get("EMPORIA_EMAIL")
    password = os.environ.get("EMPORIA_PASSWORD")
    if not email or not password:
        print("EMPORIA_EMAIL / EMPORIA_PASSWORD not set", file=sys.stderr)
        sys.exit(1)

    vue = PyEmVue()
    vue.login(username=email, password=password)

    devices = vue.get_devices()
    device_gids = [d.device_gid for d in devices]

    # Three scales in one run: instantaneous (for live kW), day-to-date, and
    # month-to-date (for the dashboard's "Today"/"This Month" stats) — avoids
    # needing to accumulate history ourselves between polls.
    usage_minute = vue.get_device_list_usage(
        deviceGids=device_gids, instant=None,
        scale=Scale.MINUTE.value, unit=Unit.KWH.value,
    )
    usage_day = vue.get_device_list_usage(
        deviceGids=device_gids, instant=None,
        scale=Scale.DAY.value, unit=Unit.KWH.value,
    )
    usage_month = vue.get_device_list_usage(
        deviceGids=device_gids, instant=None,
        scale=Scale.MONTH.value, unit=Unit.KWH.value,
    )

    def flatten(usage_dict):
        # {(gid, channel_num): usage_kwh}
        out = {}
        for gid, device in usage_dict.items():
            for channel_num, channel in device.channels.items():
                out[(gid, channel_num)] = channel.usage
        return out

    minute_map = flatten(usage_minute)
    day_map = flatten(usage_day)
    month_map = flatten(usage_month)

    channels_out = []
    for gid, device in usage_minute.items():
        for channel_num, channel in device.channels.items():
            key = (gid, channel_num)
            channels_out.append({
                "device_gid": gid,
                "channel_num": channel_num,
                "name": getattr(channel, "name", None) or f"Channel {channel_num}",
                "usage_kwh_last_min": minute_map.get(key),
                "usage_kwh_today": day_map.get(key),
                "usage_kwh_month": month_map.get(key),
            })

    result = {
        "updated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "channels": channels_out,
    }

    with open("emporia-data.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote emporia-data.json with {len(channels_out)} channels")


if __name__ == "__main__":
    main()
