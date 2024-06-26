"""Initial Revision

Revision ID: 2b00055affd5
Revises: 
Create Date: 2024-04-26 16:02:02.606762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2b00055affd5'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('meta',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.generate_ulid()'), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_deleted', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('modified_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='audit',
    comment='Record metadata'
    )
    op.create_table('customer',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('customer_type', postgresql.ENUM('INDIVIDUAL', 'SMALL_BUSINESS', 'CORPORATE', 'ENTERPRISE', name='customertype', schema='auth'), server_default='INDIVIDUAL', nullable=False),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    schema='auth',
    comment='Application end-user customers',
    info={'vertex': True, 'audited': True}
    )
    op.create_table('field',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('table_name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('field_name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('label', sa.VARCHAR(length=255), nullable=False),
    sa.Column('field_type', postgresql.ENUM('ARRAY', 'BIGINT', 'BOOLEAN', 'DATE', 'DECIMAL', 'ENUM', 'INTERVAL', 'JSON', 'TEXT', 'TIME', 'TIMESTAMP', name='fieldtype', schema='fltr'), nullable=False),
    sa.Column('includes', postgresql.ENUM('INCLUDE', 'EXCLUDE', name='include', schema='fltr'), nullable=False),
    sa.Column('matches', postgresql.ENUM('AND', 'OR', 'NOT', name='match', schema='fltr'), nullable=False),
    sa.Column('lookups', postgresql.ENUM('EQUAL', 'NOT_EQUAL', 'GREATER_THAN', 'GREATER_THAN_OR_EQUAL', 'LESS_THAN', 'LESS_THAN_OR_EQUAL', 'BETWEEN', 'IN', 'NOT_IN', 'NULL', 'NOT_NULL', 'LIKE', 'ILIKE', 'NOT_LIKE', 'NOT_ILIKE', 'STARTS_WITH', 'ENDS_WITH', 'CONTAINS', name='lookup', schema='fltr'), nullable=False),
    sa.Column('column_security', postgresql.ENUM('PUBLIC', 'PRIVATE', 'SECRET', 'SYSTEM', name='columsecurity', schema='fltr'), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('table_name', 'field_name'),
    schema='fltr',
    comment='Describes a column in a db table.',
    info={'vertex': True, 'audited': True}
    )
    op.create_index(op.f('ix_fltr_field_table_name'), 'field', ['table_name'], unique=False, schema='fltr')
    op.create_table('group',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('customer_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('parent_id', sa.VARCHAR(length=26), nullable=True),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['auth.customer.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_id'], ['auth.group.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('customer_id', 'name', name='uq_group_customer_id_name'),
    schema='auth',
    comment='Application end-user groups, child groups can be created for granular access control',
    info={'vertex': True, 'audited': True}
    )
    op.create_index(op.f('ix_auth_group_customer_id'), 'group', ['customer_id'], unique=False, schema='auth')
    op.create_index(op.f('ix_auth_group_parent_id'), 'group', ['parent_id'], unique=False, schema='auth')
    op.create_table('role',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('customer_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('description', sa.VARCHAR(), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['auth.customer.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='auth',
    comment='\n                Roles, created by end user group admins, enable assignment of group_permissions\n                by functionality, department, etc... to users.\n            ',
    info={'vertex': True, 'audited': True}
    )
    op.create_index(op.f('ix_auth_role_customer_id'), 'role', ['customer_id'], unique=False, schema='auth')
    op.create_index('ix_customer_id_name', 'role', ['customer_id', 'name'], unique=False, schema='auth')
    op.create_table('user',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), nullable=False),
    sa.Column('handle', sa.VARCHAR(length=255), nullable=False),
    sa.Column('full_name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('customer_id', sa.VARCHAR(length=26), nullable=True),
    sa.Column('is_superuser', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_customer_admin', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_verified', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_locked', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_suspended', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('suspension_expiration', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("\n                is_superuser = 'true' AND customer_id IS NULL OR\n                is_customer_admin = 'true' AND customer_id IS NOT NULL OR\n                is_superuser = 'false' AND is_customer_admin = 'false' AND customer_id IS NOT NULL\n            ", name='ck_user_is_superuser_and_not_customer_admin'),
    sa.ForeignKeyConstraint(['customer_id'], ['auth.customer.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('handle'),
    schema='auth',
    comment='Application end-users',
    info={'vertex': True, 'audited': True}
    )
    op.create_index(op.f('ix_auth_user_customer_id'), 'user', ['customer_id'], unique=False, schema='auth')
    op.create_table('access_log',
    sa.Column('id', sa.BIGINT(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('action_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('action', postgresql.ENUM('LOGIN', 'TOKEN_ISSUED', 'TOKEN_RENEWED', 'TOKEN_RENEWAL_FAILURE', 'LOGOUT', 'LOCKED', 'UNLOCKED', 'FAILED_LOGIN', 'PASSWORD_CHANGE', 'PASSWORD_RESET', 'FORBIDDEN_ERROR', name='accesslogaction', schema='audit'), nullable=False),
    sa.Column('message', sa.VARCHAR(length=255), nullable=False),
    sa.Column('severity', postgresql.ENUM('LOGIN', 'TOKEN_ISSUED', 'TOKEN_RENEWED', 'TOKEN_RENEWAL_FAILURE', 'LOGOUT', 'LOCKED', 'UNLOCKED', 'FAILED_LOGIN', 'PASSWORD_CHANGE', 'PASSWORD_RESET', 'FORBIDDEN_ERROR', name='accesslogseverity', schema='audit'), nullable=False),
    sa.Column('client_hint_hash', sa.VARCHAR(length=128), nullable=True),
    sa.Column('token', sa.VARCHAR(length=128), nullable=True),
    sa.Column('token_renewal_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='audit',
    comment='Application end-user access log'
    )
    op.create_index(op.f('ix_audit_access_log_user_id'), 'access_log', ['user_id'], unique=False, schema='audit')
    op.create_table('group_permission',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('group_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('permissions', postgresql.ARRAY(postgresql.ENUM('CREATE', 'READ', 'UPDATE', 'DELETE', name='permission', schema='auth')), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['auth.group.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'name', name='uq_group_permission_name'),
    sa.UniqueConstraint('group_id', 'permissions', name='uq_group_permission_permissions'),
    schema='auth',
    comment='\n                Permissions assigned to a group.\n                Created automatically by the DB via a trigger when a new group is created.\n                group_permission records are created for each group with the following combinations of permissions:\n                    [READ]\n                    [READ, CREATE]\n                    [READ, CREATE, UPDATE]\n                    [READ, CREATE, DELETE]\n                    [READ, CREATE, UPDATE, DELETE]\n                    [READ, UPDATE]\n                    [READ, UPDATE, DELETE]\n                    [READ, DELETE]\n                Deleted automatically by the DB via the FK Constraints ondelete when an group is deleted.\n            ',
    info={'vertex': True}
    )
    op.create_index(op.f('ix_auth_group_permission_group_id'), 'group_permission', ['group_id'], unique=False, schema='auth')
    op.create_table('hashed_password',
    sa.Column('id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('hashed_password', sa.VARCHAR(length=128), nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modified_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='auth',
    comment='Application end-user hashed passwords'
    )
    op.create_table('user__role',
    sa.Column('user_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('role_id', sa.VARCHAR(length=26), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['auth.role.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'role_id'),
    schema='auth',
    comment='Assigned by customer_admin users to assign roles to users based on organization requirements.',
    info={'edge': 'HAS_ROLE', 'audited': True}
    )
    op.create_index('ix_user_id__role_id', 'user__role', ['user_id', 'role_id'], unique=False, schema='auth')
    op.create_table('filter',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('group_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('field_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('lookup', postgresql.ENUM('EQUAL', 'NOT_EQUAL', 'GREATER_THAN', 'GREATER_THAN_OR_EQUAL', 'LESS_THAN', 'LESS_THAN_OR_EQUAL', 'BETWEEN', 'IN', 'NOT_IN', 'NULL', 'NOT_NULL', 'LIKE', 'ILIKE', 'NOT_LIKE', 'NOT_ILIKE', 'STARTS_WITH', 'ENDS_WITH', 'CONTAINS', name='lookup', schema='fltr'), nullable=False),
    sa.Column('include', postgresql.ENUM('INCLUDE', 'EXCLUDE', name='include', schema='fltr'), nullable=False),
    sa.Column('match', postgresql.ENUM('AND', 'OR', 'NOT', name='match', schema='fltr'), nullable=False),
    sa.Column('bigint_value', sa.BIGINT(), nullable=True),
    sa.Column('boolean_value', sa.BOOLEAN(), nullable=True),
    sa.Column('date_value', sa.DATE(), nullable=True),
    sa.Column('decimal_value', sa.NUMERIC(), nullable=True),
    sa.Column('related_table', sa.VARCHAR(length=255), nullable=True),
    sa.Column('related_id', sa.VARCHAR(length=26), nullable=True),
    sa.Column('string_value', sa.VARCHAR(length=255), nullable=True),
    sa.Column('text_value', sa.VARCHAR(), nullable=True),
    sa.Column('time_value', postgresql.TIME(), nullable=True),
    sa.Column('timestamp_value', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint('\n                bigint_value IS NOT NULL\n                OR boolean_value IS NOT NULL\n                OR date_value IS NOT NULL\n                OR decimal_value IS NOT NULL\n                OR related_id IS NOT NULL AND related_table IS NOT NULL\n                OR text_value IS NOT NULL\n                OR time_value IS NOT NULL\n                OR timestamp_value IS NOT NULL\n            ', name='ck_filter_value'),
    sa.CheckConstraint('\n                related_id IS NOT NULL AND related_table IS NOT NULL\n                OR related_id IS NULL AND related_table IS NULL\n            ', name='ck_related_object'),
    sa.ForeignKeyConstraint(['field_id'], ['fltr.field.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['auth.group.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'field_id', 'lookup', 'include', 'match', 'bigint_value', 'boolean_value', 'date_value', 'decimal_value', 'related_table', 'related_id', 'string_value', 'text_value', 'time_value', 'timestamp_value', postgresql_nulls_not_distinct=True),
    schema='fltr',
    comment='A db column bound to a value.',
    info={'vertex': True, 'audited': True}
    )
    op.create_index('ix_filter__unique_together', 'filter', ['group_id', 'field_id', 'lookup', 'include', 'match'], unique=False, schema='fltr')
    op.create_index(op.f('ix_fltr_filter_field_id'), 'filter', ['field_id'], unique=False, schema='fltr')
    op.create_index(op.f('ix_fltr_filter_group_id'), 'filter', ['group_id'], unique=False, schema='fltr')
    op.create_index(op.f('ix_fltr_filter_user_id'), 'filter', ['user_id'], unique=False, schema='fltr')
    op.create_table('query',
    sa.Column('id', sa.VARCHAR(length=26), server_default=sa.text('audit.insert_meta_record()'), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('group_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=False),
    sa.Column('object_type', sa.VARCHAR(length=255), nullable=False),
    sa.Column('show_with_object', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
    sa.Column('include_values', postgresql.ENUM('INCLUDE', 'EXCLUDE', name='include', schema='fltr'), nullable=False),
    sa.Column('match_values', postgresql.ENUM('AND', 'OR', 'NOT', name='match', schema='fltr'), nullable=False),
    sa.Column('include_subqueries', postgresql.ENUM('INCLUDE', 'EXCLUDE', name='include', schema='fltr'), nullable=False),
    sa.Column('match_subqueries', postgresql.ENUM('AND', 'OR', 'NOT', name='match', schema='fltr'), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['auth.group.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id'], ['audit.meta.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth.user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'name'),
    schema='fltr',
    comment='Filter queries',
    info={'vertex': True, 'audited': True}
    )
    op.create_index(op.f('ix_fltr_query_group_id'), 'query', ['group_id'], unique=False, schema='fltr')
    op.create_index(op.f('ix_fltr_query_user_id'), 'query', ['user_id'], unique=False, schema='fltr')
    op.create_index('ix_group_id_name_user_query', 'query', ['group_id', 'name'], unique=False, schema='fltr')
    op.create_table('role__group_permission',
    sa.Column('role_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('group_permission_id', sa.VARCHAR(length=26), nullable=False),
    sa.ForeignKeyConstraint(['group_permission_id'], ['auth.group_permission.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['auth.role.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('role_id', 'group_permission_id'),
    schema='auth',
    comment='Assigned by customer_admin users to assign group_permissions to roles based on organization requirements.',
    info={'edge': 'HAS_GROUP_PERMISSION', 'audited': True}
    )
    op.create_index('ix_role_id__group_permission_id', 'role__group_permission', ['role_id', 'group_permission_id'], unique=False, schema='auth')
    op.create_table('query__filter',
    sa.Column('query_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('filter_id', sa.VARCHAR(length=26), nullable=False),
    sa.ForeignKeyConstraint(['filter_id'], ['fltr.filter.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['query_id'], ['fltr.query.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('query_id', 'filter_id'),
    schema='fltr',
    info={'edge': 'HAS_FILTER', 'audited': True}
    )
    op.create_table('query__subquery',
    sa.Column('query_id', sa.VARCHAR(length=26), nullable=False),
    sa.Column('subquery_id', sa.VARCHAR(length=26), nullable=False),
    sa.ForeignKeyConstraint(['query_id'], ['fltr.query.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['subquery_id'], ['fltr.query.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('query_id', 'subquery_id'),
    schema='fltr',
    info={'edge': 'HAS_SUBQUERY', 'audited': True}
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('query__subquery', schema='fltr')
    op.drop_table('query__filter', schema='fltr')
    op.drop_index('ix_role_id__group_permission_id', table_name='role__group_permission', schema='auth')
    op.drop_table('role__group_permission', schema='auth')
    op.drop_index('ix_group_id_name_user_query', table_name='query', schema='fltr')
    op.drop_index(op.f('ix_fltr_query_user_id'), table_name='query', schema='fltr')
    op.drop_index(op.f('ix_fltr_query_group_id'), table_name='query', schema='fltr')
    op.drop_table('query', schema='fltr')
    op.drop_index(op.f('ix_fltr_filter_user_id'), table_name='filter', schema='fltr')
    op.drop_index(op.f('ix_fltr_filter_group_id'), table_name='filter', schema='fltr')
    op.drop_index(op.f('ix_fltr_filter_field_id'), table_name='filter', schema='fltr')
    op.drop_index('ix_filter__unique_together', table_name='filter', schema='fltr')
    op.drop_table('filter', schema='fltr')
    op.drop_index('ix_user_id__role_id', table_name='user__role', schema='auth')
    op.drop_table('user__role', schema='auth')
    op.drop_table('hashed_password', schema='auth')
    op.drop_index(op.f('ix_auth_group_permission_group_id'), table_name='group_permission', schema='auth')
    op.drop_table('group_permission', schema='auth')
    op.drop_index(op.f('ix_audit_access_log_user_id'), table_name='access_log', schema='audit')
    op.drop_table('access_log', schema='audit')
    op.drop_index(op.f('ix_auth_user_customer_id'), table_name='user', schema='auth')
    op.drop_table('user', schema='auth')
    op.drop_index('ix_customer_id_name', table_name='role', schema='auth')
    op.drop_index(op.f('ix_auth_role_customer_id'), table_name='role', schema='auth')
    op.drop_table('role', schema='auth')
    op.drop_index(op.f('ix_auth_group_parent_id'), table_name='group', schema='auth')
    op.drop_index(op.f('ix_auth_group_customer_id'), table_name='group', schema='auth')
    op.drop_table('group', schema='auth')
    op.drop_index(op.f('ix_fltr_field_table_name'), table_name='field', schema='fltr')
    op.drop_table('field', schema='fltr')
    op.drop_table('customer', schema='auth')
    op.drop_table('meta', schema='audit')
    # ### end Alembic commands ###
