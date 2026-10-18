from django.db import models


# select_related paths that load a farm's units with everything above them (both
# branches are at most three levels deep) in the same query as the farm
FARM_UNITS_RELATED = (
    'administrative_unit__parent__parent',
    'location_unit__parent__parent',
)


class AdministrativeUnit(models.Model):
    """
    One node in a country's administrative hierarchy, e.g.
    Kenya has two branches under each county:
      County government:   County -> Sub-County -> Ward
      National government: County -> Location -> Sub-Location
    Village and clan are typed in on the farm rather than picked from here.

    Top-level units (counties) have no parent; every other unit points to the
    unit directly above it.
    """
    COUNTY = 'COUNTY'
    # Levels of each branch, top to bottom
    ADMINISTRATIVE_LEVELS = ('COUNTY', 'SUB_COUNTY', 'WARD')
    NATIONAL_LEVELS = ('LOCATION', 'SUB_LOCATION')

    SUB_COUNTY = 'SUB_COUNTY'
    WARD = 'WARD'
    LOCATION = 'LOCATION'
    SUB_LOCATION = 'SUB_LOCATION'
    LEVEL_CHOICES = [
        (COUNTY, 'County'),
        (SUB_COUNTY, 'Sub-County'),
        (WARD, 'Ward'),
        (LOCATION, 'Location'),
        (SUB_LOCATION, 'Sub-Location'),
    ]

    unit_id = models.AutoField(primary_key=True)
    country = models.ForeignKey('Country', on_delete=models.PROTECT, related_name='administrative_units')
    parent = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='children'
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    record_version = models.IntegerField(default=1)
    date_time_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField(null=True, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    date_time_modified = models.DateTimeField(auto_now=True)
    modified_by = models.IntegerField(null=True, blank=True)
    latest_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'administrative_units'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['country', 'parent', 'level', 'name'], name='unique_unit_name_per_parent'
            ),
            # NULL parents are never equal in SQL, so top-level names need their own rule
            models.UniqueConstraint(
                fields=['country', 'name'],
                condition=models.Q(parent__isnull=True),
                name='unique_top_level_unit_name',
            ),
        ]
        indexes = [
            models.Index(fields=['country', 'parent']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

    def ancestors(self):
        """Units above this one, ordered from the top level down."""
        chain = []
        node = self.parent
        while node is not None:
            chain.append(node)
            node = node.parent
        return list(reversed(chain))
