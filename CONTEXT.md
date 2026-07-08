# HADR Monitor

How raw records from GDACS, USGS and ReliefWeb become the Disasters and
Sitrep this system publishes each morning.

## Language

**Disaster**:
One real-world calamity, merged from one or more feed Reports via entity
resolution. The system's core entity — generically modelled (open hazard
type) even though v1 only ever populates it from natural-hazard feeds.
_Avoid_: Event, Incident, Hazard.

**Report**:
A single feed's record contributing evidence toward a Disaster — one USGS
GeoJSON feature, one GDACS event+episode, one ReliefWeb RSS item. Several
Reports, across feeds or within one, can point to the same Disaster.
_Avoid_: Record, Entry, Item.

**Episode**:
GDACS's own unit of revision within one GDACS event: a new episode means
GDACS has issued an updated severity assessment for the same underlying
event. Escalation is detected by comparing episodes, not raw score deltas.
_Avoid_: Revision, Update.

**GLIDE number**:
A cross-agency disaster identifier (e.g. `EQ-2026-000093-VEN`). When present
on a Report, it is the primary key entity resolution merges on. Present on
most ReliefWeb records, sometimes on GDACS, never on USGS.

**Hazard type**:
The open-ended classification of what kind of calamity a Disaster is
(earthquake, cyclone, flood, ...). Deliberately not a closed enum of
GDACS's 7 types, so a future non-natural-hazard source can populate it
without a schema change.
_Avoid_: Category.

**Sitrep**:
The capped, severity-ranked list of Disasters published to `dashboard.html`
at 08:30 SGT. Reserve "Sitrep" for this daily published output —
"Report" is a single feed's raw record, a distinct and unrelated thing.
_Avoid_: Digest, Summary, Report (see above).

**Escalation**:
A Disaster's severity tier increasing since it was last surfaced (e.g.
GDACS Orange→Red, USGS PAGER yellow→orange). One of the events that breaks
silence on an otherwise-quiet morning.
_Avoid_: Upgrade.

**Correction**:
A sitrep entry reflecting a change to an already-surfaced Disaster's
underlying data — a revised magnitude, a retracted USGS event — that does
not cross a severity tier. Amends forward; never rewrites an
already-published Sitrep.
_Avoid_: Update, Fix.
