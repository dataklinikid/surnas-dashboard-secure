# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class ReadOnlyQuerySet(models.QuerySet):
    def _blocked(self, *args, **kwargs):
        raise RuntimeError("Database reporting survei bersifat read-only.")

    create = _blocked
    bulk_create = _blocked
    bulk_update = _blocked
    update = _blocked
    delete = _blocked
    get_or_create = _blocked
    update_or_create = _blocked
    acreate = _blocked
    abulk_create = _blocked
    abulk_update = _blocked
    aupdate = _blocked
    adelete = _blocked
    aget_or_create = _blocked
    aupdate_or_create = _blocked


class ReadOnlyModel(models.Model):
    objects = ReadOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        raise RuntimeError("Database reporting survei bersifat read-only.")

    def save_base(self, *args, **kwargs):
        raise RuntimeError("Database reporting survei bersifat read-only.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Database reporting survei bersifat read-only.")


class Cases(ReadOnlyModel):
    id = models.TextField(primary_key=True)
    key = models.TextField()
    label = models.TextField()
    questionnaire = models.TextField(blank=True, null=True)
    last_modified_revision = models.IntegerField()
    deleted = models.IntegerField()
    verified = models.IntegerField()
    partial_save_mode = models.TextField(blank=True, null=True)
    partial_save_field_name = models.TextField(blank=True, null=True)
    partial_save_level_key = models.TextField(blank=True, null=True)
    partial_save_record_occurrence = models.IntegerField(blank=True, null=True)
    partial_save_item_occurrence = models.IntegerField(blank=True, null=True)
    partial_save_subitem_occurrence = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cases'


class CsproJobs(ReadOnlyModel):
    start_caseid = models.PositiveIntegerField()
    start_revision = models.PositiveIntegerField()
    end_caseid = models.PositiveIntegerField()
    end_revision = models.PositiveIntegerField()
    cases_to_process = models.PositiveIntegerField(blank=True, null=True)
    cases_processed = models.PositiveIntegerField(blank=True, null=True)
    status = models.PositiveIntegerField()
    created_time = models.DateTimeField()
    modified_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cspro_jobs'


class CsproMeta(ReadOnlyModel):
    cspro_version = models.TextField()
    dictionary = models.TextField()
    source_modified_time = models.DateTimeField()
    created_time = models.DateTimeField()
    modified_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cspro_meta'


class H0(ReadOnlyModel):
    h0_id = models.AutoField(db_column='h0-id', primary_key=True)  # Field renamed to remove unsuitable characters.
    level_1_id = models.ForeignKey('Level1', models.DO_NOTHING, db_column='level-1-id')  # Field renamed to remove unsuitable characters.
    q_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_d = models.TextField(blank=True, null=True)
    q_d1 = models.TextField(blank=True, null=True)
    q_e = models.TextField(blank=True, null=True)
    q_f = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_g = models.TextField(blank=True, null=True)
    q_h = models.TextField(blank=True, null=True)
    q_i = models.TextField(blank=True, null=True)
    q_rt = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_rw = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_j = models.DecimalField(max_digits=13, decimal_places=0, blank=True, null=True)
    q_k = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_l = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_l0 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_l0l = models.TextField(blank=True, null=True)
    q_m_jam = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_m_mnt = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_1 = models.DecimalField(max_digits=3, decimal_places=0, blank=True, null=True)
    q_2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_2l = models.TextField(blank=True, null=True)
    q_3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_3l = models.TextField(blank=True, null=True)
    q_4 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_5 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_6 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_7 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_8 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_9 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_10 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_11 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_12 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_13 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_14 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_15 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_16 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_17 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_18 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_19 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_20 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_21 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_22 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_23 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_24 = models.TextField(blank=True, null=True)
    q_25 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_26 = models.TextField(blank=True, null=True)
    q_27 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_28 = models.TextField(blank=True, null=True)
    q_29 = models.TextField(blank=True, null=True)
    q_30_1 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_4 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_5 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_6 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_7 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_8 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_9 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_10 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_11 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_12 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_13 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_14 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_15 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_30_16 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_1 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_4 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_5 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_31_6 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_1 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_4 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_5 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_6 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_7 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_32_8 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_33 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_34 = models.TextField(blank=True, null=True)
    q_34c_1_field = models.DecimalField(db_column='q_34c(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_2_field = models.DecimalField(db_column='q_34c(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_3_field = models.DecimalField(db_column='q_34c(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_4_field = models.DecimalField(db_column='q_34c(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_5_field = models.DecimalField(db_column='q_34c(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_6_field = models.DecimalField(db_column='q_34c(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34c_7_field = models.DecimalField(db_column='q_34c(7)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_34l = models.TextField(blank=True, null=True)
    q_35 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_36 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_37 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_38 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_39 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_b = models.TextField(blank=True, null=True)
    q_40_bc_1_field = models.DecimalField(db_column='q_40_bc(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_2_field = models.DecimalField(db_column='q_40_bc(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_3_field = models.DecimalField(db_column='q_40_bc(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_4_field = models.DecimalField(db_column='q_40_bc(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_5_field = models.DecimalField(db_column='q_40_bc(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_6_field = models.DecimalField(db_column='q_40_bc(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bc_7_field = models.DecimalField(db_column='q_40_bc(7)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_bl = models.TextField(blank=True, null=True)
    q_40_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_f = models.TextField(blank=True, null=True)
    q_40_fc_1_field = models.DecimalField(db_column='q_40_fc(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fc_2_field = models.DecimalField(db_column='q_40_fc(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fc_3_field = models.DecimalField(db_column='q_40_fc(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fc_4_field = models.DecimalField(db_column='q_40_fc(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fc_5_field = models.DecimalField(db_column='q_40_fc(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fc_6_field = models.DecimalField(db_column='q_40_fc(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_fl = models.TextField(blank=True, null=True)
    q_40_g = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_h = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_40_i = models.TextField(blank=True, null=True)
    q_40_ic_1_field = models.DecimalField(db_column='q_40_ic(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_2_field = models.DecimalField(db_column='q_40_ic(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_3_field = models.DecimalField(db_column='q_40_ic(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_4_field = models.DecimalField(db_column='q_40_ic(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_5_field = models.DecimalField(db_column='q_40_ic(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_6_field = models.DecimalField(db_column='q_40_ic(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_7_field = models.DecimalField(db_column='q_40_ic(7)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_8_field = models.DecimalField(db_column='q_40_ic(8)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_ic_9_field = models.DecimalField(db_column='q_40_ic(9)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_40_il = models.TextField(blank=True, null=True)
    q_41 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_42 = models.TextField(blank=True, null=True)
    q_43 = models.TextField(blank=True, null=True)
    q_44 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_45 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_46 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_47 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_48 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_49 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_50 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_51 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_52 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_53 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_54 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_55 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_56 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_57 = models.TextField(blank=True, null=True)
    q_57c_1_field = models.DecimalField(db_column='q_57c(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_57c_2_field = models.DecimalField(db_column='q_57c(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_57c_3_field = models.DecimalField(db_column='q_57c(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_57c_4_field = models.DecimalField(db_column='q_57c(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_57c_5_field = models.DecimalField(db_column='q_57c(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_57c_6_field = models.DecimalField(db_column='q_57c(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_58 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_59 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_60 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_61 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_62 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_63 = models.TextField(blank=True, null=True)
    q_63c_1_field = models.DecimalField(db_column='q_63c(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_2_field = models.DecimalField(db_column='q_63c(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_3_field = models.DecimalField(db_column='q_63c(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_4_field = models.DecimalField(db_column='q_63c(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_5_field = models.DecimalField(db_column='q_63c(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_6_field = models.DecimalField(db_column='q_63c(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63c_7_field = models.DecimalField(db_column='q_63c(7)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_63l = models.TextField(blank=True, null=True)
    q_64 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_65 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_65l = models.TextField(blank=True, null=True)
    q_66 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_67 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_67l = models.TextField(blank=True, null=True)
    q_68 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_69 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_69l = models.TextField(blank=True, null=True)
    q_70 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_71 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_72 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_73 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_74 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_75 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_76 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_77 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_78 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_79 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_80 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_81 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_82 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_g = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_h = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_i = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_j = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_k = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_l = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_m = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_n = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_83_o = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_84 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_85 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_86_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_87_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_87_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_87_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_87_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_88_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_88_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_88_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_88_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_89_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_89_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_89_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_89_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_90_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_90_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_90_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_90_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_90_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_91 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_92 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_93 = models.TextField(blank=True, null=True)
    q_94 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_95 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_96 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_97 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_98 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_99 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_100 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_101 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_102 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_103 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_104 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_105 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_106 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_107 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_108 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_109 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_110 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_110l = models.TextField(blank=True, null=True)
    q_111 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_112 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_113 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_114 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_115 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_116 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_117 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_118 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_119 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_120 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_121 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_122 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_123 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_124 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_125 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_126 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_127 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_128 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_129 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_130 = models.TextField(blank=True, null=True)
    q_130c_1_field = models.DecimalField(db_column='q_130c(1)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_2_field = models.DecimalField(db_column='q_130c(2)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_3_field = models.DecimalField(db_column='q_130c(3)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_4_field = models.DecimalField(db_column='q_130c(4)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_5_field = models.DecimalField(db_column='q_130c(5)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_6_field = models.DecimalField(db_column='q_130c(6)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_7_field = models.DecimalField(db_column='q_130c(7)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_8_field = models.DecimalField(db_column='q_130c(8)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130c_9_field = models.DecimalField(db_column='q_130c(9)', max_digits=1, decimal_places=0, blank=True, null=True)  # Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    q_130l = models.TextField(blank=True, null=True)
    q_131_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_g = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_h = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_i = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_j = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_k = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_l = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_m = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_n = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_o = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_p = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_q = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_r = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_s = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_131_t = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_132_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_133_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_134_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_134_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_134_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_134_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_135 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_136 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_a = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_b = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_c = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_d = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_e = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_f = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_g = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_h = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_137_i = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_138 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_139 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_140 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_141 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_142 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_143 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_143l = models.TextField(blank=True, null=True)
    q_144 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_145 = models.TextField(blank=True, null=True)
    q_146_1 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_4 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_5 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_6 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_7 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_8 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_9 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_10 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_11 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_12 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_13 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_14 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_15 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_16 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_17 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_18 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_19 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_20 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_21 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_22 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_23 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_24 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_25 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_26 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_27 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_28 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_29 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_30 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_31 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_32 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_33 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_34 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_35 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_146_36 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_147 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_148 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_149 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_149l = models.TextField(blank=True, null=True)
    q_150 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_151 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_152 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_152l = models.TextField(blank=True, null=True)
    q_153 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_154 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_155 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_156 = models.TextField(blank=True, null=True)
    q_157 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_158 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_159 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_159l = models.TextField(blank=True, null=True)
    q_l1 = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_l1l = models.TextField(blank=True, null=True)
    q_l2 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_l3 = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_n = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_o = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_p = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_q = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_r = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_s = models.TextField(blank=True, null=True)
    q_t = models.TextField(blank=True, null=True)
    q_u = models.DecimalField(max_digits=1, decimal_places=0, blank=True, null=True)
    q_ul = models.TextField(blank=True, null=True)
    q_v = models.TextField(blank=True, null=True)
    q_w = models.DecimalField(max_digits=13, decimal_places=0, blank=True, null=True)
    q_x_jam = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_x_mnt = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    q_ac = models.DecimalField(max_digits=4, decimal_places=0, blank=True, null=True)
    date = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    month = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    year = models.DecimalField(max_digits=4, decimal_places=0, blank=True, null=True)
    hour = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    minute = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    hari = models.TextField(blank=True, null=True)
    waktu = models.TextField(blank=True, null=True)
    hpid = models.TextField(blank=True, null=True)
    usrnm = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'h0'


class Level1(ReadOnlyModel):
    level_1_id = models.AutoField(db_column='level-1-id', primary_key=True)  # Field renamed to remove unsuitable characters.
    case_id = models.TextField(db_column='case-id', unique=True)  # Field renamed to remove unsuitable characters.
    q_a = models.DecimalField(max_digits=4, decimal_places=0, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'level-1'


class Notes(ReadOnlyModel):
    case_id = models.TextField()
    field_name = models.TextField()
    level_key = models.TextField()
    record_occurrence = models.IntegerField()
    item_occurrence = models.IntegerField()
    subitem_occurrence = models.IntegerField()
    content = models.TextField()
    operator_id = models.TextField()
    modified_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'notes'
