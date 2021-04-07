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
import random
import time

from django.db.models import F
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from readability import feed
from readability import models
from readability import util


@db_periodic_task(crontab(minute='*' if util.DEBUG else '*/10'))
def ScheduleFeedUpdates():
  """Periodically check for stale feeds, schedule tasks to update them."""
  for feed_e in models.Feed.objects.order_by(
      F('last_fetch_time') + F('fetch_interval_seconds')):
    # TODO: Check for within next N seconds (matching crontab), schedule then.
    update_time = feed_e.last_fetch_time + feed_e.fetch_interval_seconds
    now = time.time()
    d = max(0, update_time - now)
    if d > 50:
      util.log.info(
          'Next update too far in the future (%.3f seconds, %.3f minutes)',
          d, d/60)
      break

    util.log.info('Scheduling update (in %.3f seconds) of %s ...', d, feed_e.url)
    feed.UpdateFeed.schedule((feed_e.url,), delay=d)


@db_periodic_task(crontab(minute=11))
def StaleEntryCleanup():
  """Delete stale entries older than those that will be served."""
  for feed_e in models.Feed.objects.all():
    stale_keys = feed_e.stale_entries.values_list('pk', flat=True)
    models.Entry.objects.filter(pk__in=stale_keys).delete()
