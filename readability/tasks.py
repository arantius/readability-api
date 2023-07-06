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

def period(period):
  """A Huey validator to run periodic tasks with a minimum period.

  Unlike `crontab()` you need not specify wall-clock times.  The task will run
  once immediately at (interpreter) start up, then no more often than once per
  `period`, which is a `datetime.Timedelta`.

  Due to how Huey implements periodic tasks, any period below 60 seconds will
  effectively be 60 seconds.
  """
  previous_dt = None
  def validator(dt):
    nonlocal previous_dt
    if not previous_dt or \
        (previous_dt + period - datetime.timedelta(seconds=1)) < dt:
      previous_dt = dt
      return True
    return False
  return validator


@db_periodic_task(period(datetime.timedelta(
    minutes=1 if util.DEBUG else 10)))
def ScheduleFeedUpdates():
  """Periodically check for stale feeds, schedule tasks to update them."""
  # Don't schedule for this many seconds, to avoid double-scheduling. E.g.
  # we run every N minutes, the next check is in N minutes plus one MS.
  # We schedule a check now, and then in N minutes we check and the next
  # fetch is still in the future -- that scheduled check hasn't completed
  # -- so we schedule a second!  Pick a duration that should be longer
  # than any `feed.UpdateFeed()` execution, so it's always updated the
  # feed before we check again.
  jitter_sec = 15

  now = time.time()
  for feed_e in models.Feed.objects.order_by(
      F('last_fetch_time') + F('fetch_interval_seconds')):
    update_time = feed_e.last_fetch_time + feed_e.fetch_interval_seconds
    delay = max(0, update_time - now)
    update_freq_limit = ((1 if util.DEBUG else 10) * 60 - jitter_sec)
    if delay > update_freq_limit:  # as period above
      # 2022-03-07 Very noisy to logs!
      #util.log.info(
      #    'Skip feed update for %r: (%.3f seconds, %.3f minutes) '
      #    '> limit (%.3f seconds)',
      #    feed_e.url, delay, delay/60, update_freq_limit)
      continue

    util.log.info(
        'Scheduling update (in %.3f seconds) of %s ...', delay, feed_e.url)
    feed.UpdateFeed.schedule((feed_e.url,), delay=delay)


@db_periodic_task(period(datetime.timedelta(hours=1)))
def StaleEntryCleanup():
  """Delete stale entries older than those that will be served."""
  for feed_e in models.Feed.objects.all():
    stale_keys = feed_e.stale_entries.values_list('pk', flat=True)
    models.Entry.objects.filter(pk__in=stale_keys).delete()
  util.RequestsCacheSession().remove_expired_responses()
