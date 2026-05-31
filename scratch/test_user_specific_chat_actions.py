import os
import sys

# 將專案根目錄加入 path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import models
from routers.chat import toggle_archive_room, delete_chat_room, get_chat_rooms

def test_user_specific_flows():
    print("=== Start User-Specific Chat Actions Validation ===")
    
    db = database.SessionLocal()
    try:
        # 1. 取得測試資料
        buyer = db.query(models.User).filter(models.User.id == 2).first()
        seller = db.query(models.User).filter(models.User.id == 1).first()
        product = db.query(models.Product).filter(models.Product.id == 1).first()
        
        if not buyer or not seller or not product:
            print("[ERROR] Test data insufficient. Ensure User ID 2 (StevenLee), User ID 1 (4113056033), and Product ID 1 exist.")
            sys.exit(1)
            
        print(f"[OK] Found buyer: {buyer.username} (ID: {buyer.id})")
        print(f"[OK] Found seller: {seller.username} (ID: {seller.id})")
        print(f"[OK] Found product: {product.name} (ID: {product.id})")
        
        # 2. 清理舊測試聊天室
        existing_rooms = db.query(models.ChatRoom).filter(
            models.ChatRoom.product_id == product.id,
            models.ChatRoom.buyer_id == buyer.id
        ).all()
        for r in existing_rooms:
            db.query(models.ChatMessage).filter(models.ChatMessage.room_id == r.id).delete()
            db.delete(r)
        db.commit()
        print("[OK] Pre-test cleanup completed.")
        
        # 3. 建立新聊天室
        test_room = models.ChatRoom(
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            buyer_archived=False,
            seller_archived=False,
            buyer_deleted=False,
            seller_deleted=False
        )
        db.add(test_room)
        db.commit()
        db.refresh(test_room)
        room_id = test_room.id
        print(f"[OK] ChatRoom created: ID {room_id}")

        buyer_context = {"user_id": buyer.id, "sub": buyer.username}
        seller_context = {"user_id": seller.id, "sub": seller.username}

        # ----------------------------------------------------
        # 測試一：對話封存獨立性 (User-Specific Archive)
        # ----------------------------------------------------
        print("\n[Test 1] Testing User-Specific Archive...")
        
        # 買家封存對話
        res_arch = toggle_archive_room(room_id=room_id, db=db, user=buyer_context)
        assert res_arch["success"] is True
        assert res_arch["is_archived"] is True, "Buyer should see is_archived=True"
        
        # 檢查買家 API
        buyer_rooms = get_chat_rooms(db=db, user=buyer_context)
        buyer_r = next((r for r in buyer_rooms if r["room_id"] == room_id), None)
        assert buyer_r is not None
        assert buyer_r["is_archived"] is True, "Buyer's room list should show archived"

        # 檢查賣家 API
        seller_rooms = get_chat_rooms(db=db, user=seller_context)
        seller_r = next((r for r in seller_rooms if r["room_id"] == room_id), None)
        assert seller_r is not None
        assert seller_r["is_archived"] is False, "Seller's room list should NOT show archived"
        print("[OK] User-Specific Archive passed: Only buyer shows archived, seller remains active.")

        # ----------------------------------------------------
        # 測試二：對話刪除獨立性與隱藏 (User-Specific Delete/Hide)
        # ----------------------------------------------------
        print("\n[Test 2] Testing User-Specific Delete...")
        
        # 買家刪除對話
        res_del = delete_chat_room(room_id=room_id, db=db, user=buyer_context)
        assert res_del["success"] is True
        
        # 重新整理 DB
        db.refresh(test_room)
        assert test_room.buyer_deleted is True, "buyer_deleted should be True"
        assert test_room.seller_deleted is False, "seller_deleted should remain False"
        
        # 檢查買家 API (不應該出現在列表中)
        buyer_rooms = get_chat_rooms(db=db, user=buyer_context)
        buyer_r = next((r for r in buyer_rooms if r["room_id"] == room_id), None)
        assert buyer_r is None, "Room should be filtered out (hidden) for buyer"
        
        # 檢查賣家 API (賣家依然要看得到對話)
        seller_rooms = get_chat_rooms(db=db, user=seller_context)
        seller_r = next((r for r in seller_rooms if r["room_id"] == room_id), None)
        assert seller_r is not None, "Room should still exist for seller"
        print("[OK] User-Specific Delete passed: Buyer hides the room, seller retains it.")

        # ----------------------------------------------------
        # 測試三：新訊息傳入時自動還原重現對話 (Undelete upon new message)
        # ----------------------------------------------------
        print("\n[Test 3] Simulating new message from seller (should undelete for buyer)...")
        # 模擬賣家發送新訊息 (在資料庫新增一條，並重置刪除狀態)
        new_msg = models.ChatMessage(
            room_id=room_id,
            sender_id=seller.id,
            message="Hey! Are you still there?"
        )
        db.add(new_msg)
        
        # 還原刪除標記
        test_room.buyer_deleted = False
        test_room.seller_deleted = False
        db.commit()
        
        # 再次檢查買家 API (對話框應該重新出現！)
        buyer_rooms = get_chat_rooms(db=db, user=buyer_context)
        buyer_r = next((r for r in buyer_rooms if r["room_id"] == room_id), None)
        assert buyer_r is not None, "Room should reappear for buyer upon new message"
        assert buyer_r["last_message"] == "Hey! Are you still there?"
        print("[OK] Chat undelete recovery passed: Room successfully reappeared for buyer.")

        # ----------------------------------------------------
        # 測試四：雙方皆刪除對話時實施物理級聯清除
        # ----------------------------------------------------
        print("\n[Test 4] Testing physical cascade cleanup when both users delete...")
        
        # 買家再次刪除對話
        delete_chat_room(room_id=room_id, db=db, user=buyer_context)
        # 賣家也刪除對話
        delete_chat_room(room_id=room_id, db=db, user=seller_context)
        
        # 檢查資料庫是否已物理清空
        deleted_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
        deleted_msgs = db.query(models.ChatMessage).filter(models.ChatMessage.room_id == room_id).all()
        assert deleted_room is None, "Room should be physically deleted"
        assert len(deleted_msgs) == 0, "Messages should be physically deleted"
        print("[OK] Physical cascade cleanup passed: Room and messages completely cleared.")

        print("\n=======================================================")
        print("CONGRATULATIONS! ALL USER-SPECIFIC FLOW TESTS PASSED!")
        print("=======================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_user_specific_flows()
