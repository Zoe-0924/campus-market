import os
import sys
# 解決路徑問題，將專案根目錄加入路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
import auth_utils
import database
import models

def test_chat_room_deletion_and_password_change():
    print("=== Start Deletion and Password Change Validation ===")
    
    # 1. 建立獨立資料庫對談
    db = database.SessionLocal()
    try:
        # 尋找測試使用者 StevenLee (ID: 2)
        user = db.query(models.User).filter(models.User.username == "StevenLee").first()
        if not user:
            print("[Error] Test user StevenLee not found!")
            sys.exit(1)
        print(f"[OK] Found test user: {user.username} (ID: {user.id})")
        
        # 尋找第二個測試使用者 4113056033 (ID: 1)
        other_user = db.query(models.User).filter(models.User.username == "4113056033").first()
        if not other_user:
            print("[Error] Test partner 4113056033 not found!")
            sys.exit(1)
        print(f"[OK] Found test partner: {other_user.username} (ID: {other_user.id})")
        
        # 尋找測試商品
        product = db.query(models.Product).first()
        if not product:
            print("[Error] No test product found in database!")
            sys.exit(1)
        print(f"[OK] Found test product: {product.name} (ID: {product.id})")
        
        # 2. 測試對話框建立與刪除
        print("\n[Test 1] Creating temporary ChatRoom for testing deletion...")
        new_room = models.ChatRoom(
            product_id=product.id,
            buyer_id=user.id,
            seller_id=other_user.id
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        print(f"[OK] Temporary ChatRoom created successfully! ID: {new_room.id}")
        
        # 建立幾條臨時訊息
        print("[Test 2] Creating temporary ChatMessages for cascade testing...")
        msg1 = models.ChatMessage(
            room_id=new_room.id,
            sender_id=user.id,
            message="Test message 1"
        )
        msg2 = models.ChatMessage(
            room_id=new_room.id,
            sender_id=other_user.id,
            message="Test message 2"
        )
        db.add_all([msg1, msg2])
        db.commit()
        print("[OK] Temporary ChatMessages created successfully!")
        
        # 進行級聯刪除驗證
        print("[Test 3] Executing chat room cascading deletion...")
        # 1. 級聯刪除訊息
        db.query(models.ChatMessage).filter(models.ChatMessage.room_id == new_room.id).delete()
        # 2. 刪除對話框本身
        db.delete(new_room)
        db.commit()
        print("[OK] Cascading deletion database transaction completed successfully!")
        
        # 驗證資料庫中是否已完全清空
        deleted_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == new_room.id).first()
        deleted_msgs = db.query(models.ChatMessage).filter(models.ChatMessage.room_id == new_room.id).all()
        if deleted_room is None and len(deleted_msgs) == 0:
            print("[OK] Verification passed: ChatRoom and all ChatMessages deleted successfully from DB!")
        else:
            print("[Error] DB verification failed: ChatRoom or Messages still exist!")
            sys.exit(1)
            
        # 3. 測試密碼變更邏輯
        print("\n[Test 4] Testing password hashing, verify, and updating...")
        original_hash = user.password_hash
        
        # 驗證原本密碼
        test_plain_pwd = "NewSecurePassword123"
        new_hash = auth_utils.get_password_hash(test_plain_pwd)
        
        # 測試比對
        is_valid = auth_utils.verify_password(test_plain_pwd, new_hash)
        if is_valid:
            print(f"[OK] password hashing and verification is 100% matched!")
        else:
            print("[Error] password verification failed!")
            sys.exit(1)
            
        # 模擬更新使用者密碼
        user.password_hash = new_hash
        db.commit()
        print("[OK] User password hash updated in SQLite successfully!")
        
        # 恢復原狀以維護測試帳號可用性
        user.password_hash = original_hash
        db.commit()
        print("[OK] User original password hash restored successfully!")
        
        print("\nCongratulations! All password modification and cascading deletion lifecycle tests PASSED successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    test_chat_room_deletion_and_password_change()
