import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','venomwatch.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from accounts.models import UserProfile
from reports.models import SightingReport, RangerAssignment
from reports.dispatch import get_candidate_rangers

ok = lambda m: print("PASS:", m)
def fail(m):
    print("FAIL:", m); raise SystemExit(1)

# find seeded objects
kollam = SightingReport.objects.get(title='Cobra near paddy field by Kallada bridge')
thrissur = SightingReport.objects.get(title='Viper spotted behind Thrissur round bus stand')
arun = User.objects.get(username='arun_ranger')
meera = User.objects.get(username='meera_ranger')
fathima = User.objects.get(username='fathima_ranger')
admin = User.objects.get(username='authority_admin')
citizen = User.objects.get(username='john_citizen')

# --- 24. Location filter test ---
kc = get_candidate_rangers(kollam)
knames = [c['user'].username for c in kc]
print("Kollam candidates:", [(c['user'].username, c['distance_km']) for c in kc])
tc = get_candidate_rangers(thrissur)
t_names = [c['user'].username for c in tc]
print("Thrissur candidates:", t_names)
assert 'arun_ranger' in knames and 'meera_ranger' in knames, "Kollam rangers missing"
assert 'fathima_ranger' not in knames or True
# sorted by distance
dists=[c['distance_km'] for c in kc if c['distance_km'] is not None]
assert dists == sorted(dists), "not sorted by distance"
if t_names != knames: ok("candidate lists differ per report location")
else: fail("candidate lists identical for different locations")
# fathima (TVM ~50km from Kollam) should NOT be in Kollam list
assert 'fathima_ranger' not in knames, "distant ranger leaked into Kollam candidates"
ok("distant rangers excluded from Kollam report")

# --- Authority assigns via POST ---
c_auth = Client(); c_auth.force_login(admin)
r = c_auth.post(f'/reports/{kollam.pk}/assign-ranger/', {'ranger_id': arun.pk})
assert r.status_code == 302
a1 = RangerAssignment.objects.get(sighting=kollam, ranger=arun)
ok(f"assignment created #{a1.pk} status={a1.status} dist={a1.distance_km}")
kollam.refresh_from_db()
assert kollam.response_status == 'ASSIGNED'

# tamper test: assign far-away ranger to thrissur? fathima is TVM; thrissur far. Should be rejected
before = RangerAssignment.objects.filter(sighting=thrissur).count()
r = c_auth.post(f'/reports/{thrissur.pk}/assign-ranger/', {'ranger_id': fathima.pk})
thrissur_assigns = RangerAssignment.objects.filter(sighting=thrissur).count()
assert thrissur_assigns == before, "location guard failed — unrelated ranger assigned"
ok("server-side location guard rejects unrelated ranger assignment")

# --- 9/26 Ranger isolation tests ---
c_arun = Client(); c_arun.force_login(arun)
c_meera = Client(); c_meera.force_login(meera)

# Ranger A -> own assignment detail allowed + marks read
r = c_arun.get(f'/ranger/assignments/{a1.pk}/')
assert r.status_code == 200, f"own assignment denied ({r.status_code})"
a1.refresh_from_db(); assert a1.is_read and a1.read_at
ok("Ranger A can open own assignment; is_read/read_at set")

# Ranger B -> Ranger A's assignment = DENIED (404)
r = c_meera.get(f'/ranger/assignments/{a1.pk}/')
assert r.status_code == 404, f"object-level security leak ({r.status_code})"
r = c_meera.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'ACCEPT'})
assert r.status_code == 404
ok("Ranger B cannot view/touch Ranger A's assignment via URL id change")

# Ranger A -> unassigned report #thrissur = DENIED
r = c_arun.get(f'/reports/{thrissur.pk}/')
assert r.status_code == 403, f"unassigned report accessible ({r.status_code})"
ok("Ranger cannot open unassigned report (403)")

# Ranger A -> assigned report allowed
r = c_arun.get(f'/reports/{kollam.pk}/')
assert r.status_code == 200
ok("Ranger can open own assigned report")

# Ranger -> authority dashboard / all reports / assign controls = DENIED
for url in ['/dashboard/', '/reports/', f'/reports/{kollam.pk}/verify/', f'/reports/{thrissur.pk}/assign-ranger/']:
    r = c_arun.get(url)
    assert r.status_code in (302, 403) and not (r.status_code==200 and url=='/reports/'), f"leak at {url}: {r.status_code}"
r = c_arun.get('/dashboard/')
assert r.status_code == 403
r = c_arun.get('/reports/')  # redirected to ranger dashboard
assert r.status_code == 302 and '/ranger/' in r.url
r = c_arun.post(f'/reports/{kollam.pk}/response-status/', {'response_status':'EN_ROUTE'})
assert r.status_code == 403
ok("Authority dashboard/all-reports/status-writes blocked for Rangers (403/redirect)")

# Citizen -> ranger console & authority dashboard denied
c_cit = Client(); c_cit.force_login(citizen)
assert c_cit.get('/ranger/').status_code == 403
assert c_cit.get('/dashboard/').status_code == 403
ok("Citizen cannot access Ranger console or Authority dashboard")

# --- lifecycle ---
r = c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'ACCEPT'})
a1.refresh_from_db(); assert a1.status=='ACCEPTED'; arun.profile.refresh_from_db()
assert arun.profile.availability=='BUSY', "availability not BUSY after accept"
ok("ACCEPT works; ranger AVAILABLE->BUSY")

# illegal jump ACCEPTED -> COMPLETED must be rejected
r = c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'COMPLETE','outcome':'SNAKE_CAPTURED'})
a1.refresh_from_db(); assert a1.status=='ACCEPTED'
ok("illegal status skip rejected server-side")

c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'ON_THE_WAY'}); a1.refresh_from_db(); assert a1.status=='ON_THE_WAY'
c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'AT_LOCATION'}); a1.refresh_from_db(); assert a1.status=='AT_LOCATION'
# complete without outcome -> stays AT_LOCATION
c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'COMPLETE'}); a1.refresh_from_db(); assert a1.status=='AT_LOCATION'
c_arun.post(f'/ranger/assignments/{a1.pk}/update/', {'action':'COMPLETE','outcome':'SNAKE_CAPTURED','notes':'Kobra relocated to forest.'})
a1.refresh_from_db(); assert a1.status=='COMPLETED' and a1.outcome=='SNAKE_CAPTURED' and a1.completed_at
arun.profile.refresh_from_db(); assert arun.profile.availability=='AVAILABLE', "not freed after completion"
kollam.refresh_from_db(); assert kollam.response_status=='RESOLVED'
ok("full lifecycle ON_THE_WAY->AT_LOCATION->COMPLETED; ranger back AVAILABLE; report RESOLVED")

# Authority sees outcome
r = c_auth.get(f'/reports/{kollam.pk}/')
assert r.status_code==200 and b'Snake Captured' in r.content
ok("Authority report page shows final status/outcome")

# Reassignment: create new assignment after cancel flow
r = c_auth.post(f'/reports/{kollam.pk}/assign-ranger/', {'ranger_id': meera.pk})
a2 = RangerAssignment.objects.filter(sighting=kollam, ranger=meera).first()
assert a2 and a2.status=='ASSIGNED'
ok("re-assignment to another nearby ranger works")

# decline keeps available
r = c_meera.post(f'/ranger/assignments/{a2.pk}/update/', {'action':'DECLINE'})
a2.refresh_from_db(); meera.profile.refresh_from_db()
assert a2.status=='DECLINED' and meera.profile.availability=='AVAILABLE'
ok("decline works; ranger remains AVAILABLE")

print("\nALL RANGER/AUTHORITY TESTS PASSED")
