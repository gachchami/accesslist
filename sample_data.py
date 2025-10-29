from app import app, db
from models import User, Group, UserGroup, Resource, ResourceSharing, EVERYONE_ID

with app.app_context():
   db.drop_all()
   db.create_all()

   # Users
   user1 = User(name="User1")
   user2 = User(name="User2")
   user3 = User(name="User3")
   user4 = User(name="User4")
   db.session.add_all([user1, user2, user3, user4])
   db.session.flush()

   # Groups
   group1 = Group(name="Group1")
   group2 = Group(name="Group2")
   group3 = Group(name="Group3")
   db.session.add_all([group1, group2, group3])
   db.session.flush()

   # Memberships
   db.session.add_all([
      UserGroup(user_id=user1.id, group_id=group1.id),
      UserGroup(user_id=user2.id, group_id=group1.id),
      UserGroup(user_id=user3.id, group_id=group2.id),
      UserGroup(user_id=user4.id, group_id=group3.id),
   ])

   # Resources
   r1 = Resource(name="r1.pdf")
   r2 = Resource(name="r2.pdf")
   r3 = Resource(name="r3.md")
   r4 = Resource(name="r4.md")
   r5 = Resource(name="r5.md")
   r6 = Resource(name="r6.md")


   db.session.add_all([r1, r2, r3, r4, r5, r6])
   db.session.flush()

   # Shares
   db.session.add_all([
      ResourceSharing(resource_id=r1.id, subject_id=user2.id, is_group=False),
      ResourceSharing(resource_id=r1.id, subject_id=group1.id, is_group=True),
      ResourceSharing(resource_id=r1.id, subject_id=EVERYONE_ID, is_group=False),
      ResourceSharing(resource_id=r2.id, subject_id=group2.id, is_group=True),
      ResourceSharing(resource_id=r3.id, subject_id=user1.id, is_group=False),
      ResourceSharing(resource_id=r4.id, subject_id=EVERYONE_ID, is_group=False),
      ResourceSharing(resource_id=r5.id, subject_id=group1.id, is_group=True),
   ])

   db.session.commit()
   print("✅ Sample data seeded.")
