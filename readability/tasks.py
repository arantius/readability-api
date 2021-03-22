"""Scheduled tasks for Readability API project.

--------------------------------------------------------------------------------

Readability API - Clean up pages and feeds to be readable.
Copyright (C) 2010  Anthony Lieuallen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import datetime
import logging
import random
import time

from django.db.models import F
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from readability import feed
from readability import models
from readability import util


@db_periodic_task(crontab(minute='*'))
def ScheduleFeedUpdates():
  """Periodically check for stale feeds, schedule tasks to update them."""
  for feed_e in models.Feed.objects.order_by(
      F('last_fetch_time') + F('fetch_interval_seconds')):
    # TODO: Check within next N seconds (matching crontab), schedule then.
    update_time = feed_e.last_fetch_time + feed_e.fetch_interval_seconds
    now = time.time()
    if update_time > now:
      print('not yet,', update_time, '>', now, now-update_time)
      break

    feed.UpdateFeed(feed_e.url)
