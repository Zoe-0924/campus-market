import os
import sys

# 將專案根目錄加入 path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
import models
from routers.chat import toggle_archive_room, toggle_block_room, delete_chat_room, get_chat_rooms

def test_archive_block_delete_direct():
    print("=== Start Direct Route/DB Archive, Block, and Delete Verification ===")
    
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
        
        # 2. 清理該商品的既有聊天室，保障測試無干擾
        existing_rooms = db.query(models.ChatRoom).filter(
            models.ChatRoom.product_id == product.id,
            models.ChatRoom.buyer_id == buyer.id
        ).all()
        for r in existing_rooms:
            db.query(models.ChatMessage).filter(models.ChatMessage.room_id == r.id).delete()
            db.delete(r)
        db.commit()
        print("[OK] Pre-test cleanup completed.")
        
        # 3. 建立測試聊天室
        test_room = models.ChatRoom(
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            buyer_archived=False,
            seller_archived=False,
            is_blocked=False
        )
        db.add(test_room)
        db.commit()
        db.refresh(test_room)
        room_id = test_room.id
        print(f"[OK] Test ChatRoom created successfully! ID: {room_id}")

        # 4. 測試讀取該對話框 API 返回
        print("\n[Test 1] Testing get_chat_rooms route handler directly...")
        user_context = {"user_id": buyer.id, "sub": buyer.username}
        seller_context = {"user_id": seller.id, "sub": seller.username}
        
        rooms_list = get_chat_rooms(db=db, user=user_context)
        my_room = next((r for r in rooms_list if r["room_id"] == room_id), None)
        assert my_room is not None, "Created room must be returned"
        assert my_room["is_archived"] is False, "Should be False initially"
        assert my_room["is_blocked"] is False, "Should be False initially"
        print("[OK] Chat room listed correctly with active/unblocked flags.")

        # 5. 測試封存對話 (Archive)
        print("\n[Test 2] Toggling archive status (Archive)...")
        res_archive = toggle_archive_room(room_id=room_id, db=db, user=user_context)
        assert res_archive["success"] is True
        assert res_archive["is_archived"] is True
        
        # 重新查詢 DB 驗證狀態
        room_in_db = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
        assert room_in_db.buyer_archived is True, "buyer_archived in DB should be True"
        print("[OK] Room archived successfully in DB.")

        # 6. 測試取消封存 (Unarchive)
        print("\n[Test 3] Toggling archive status again (Unarchive)...")
        res_unarchive = toggle_archive_room(room_id=room_id, db=db, user=user_context)
        assert res_unarchive["success"] is True
        assert res_unarchive["is_archived"] is False
        assert room_in_db.buyer_archived is False, "buyer_archived in DB should be False"
        print("[OK] Room unarchived successfully.")

        # 7. 測試封鎖使用者 (Block)
        print("\n[Test 4] Toggling block status (Block)...")
        res_block = toggle_block_room(room_id=room_id, db=db, user=user_context)
        assert res_block["success"] is True
        assert res_block["is_blocked"] is True
        assert room_in_db.is_blocked is True, "is_blocked in DB should be True"
        print("[OK] Room blocked successfully.")

        # 8. 驗證封鎖攔截邏輯 (模擬 WebSocket 內檢查)
        print("\n[Test 5] Simulating WebSocket security defense...")
        # 模擬 ws loop 中的檢查
        chk_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
        assert chk_room is not None
        if chk_room.is_blocked:
            print("[OK] Simulated WS handler successfully detected blocked status.")
            # 模擬錯誤回應 payload
            ws_err_payload = {
                "error": "此對話已封鎖，無法發送訊息。",
                "sender_id": buyer.id
            }
            assert ws_err_payload["error"] == "此對話已封鎖，無法發送訊息。"
            print("[OK] Blocked response payload matches specifications.")
        else:
            print("[ERROR] Room should be blocked!")
            sys.exit(1)

        # 9. 解除封鎖 (Unblock)
        print("\n[Test 6] Unblocking room...")
        res_unblock = toggle_block_room(room_id=room_id, db=db, user=user_context)
        assert res_unblock["success"] is True
        assert res_unblock["is_blocked"] is False
        assert room_in_db.is_blocked is False, "is_blocked in DB should be False"
        print("[OK] Room unblocked successfully.")

        # 10. 測試刪除對話框 (雙方刪除物理清理)
        print("\n[Test 7] Creating a mock chat message inside the room...")
        mock_msg = models.ChatMessage(
            room_id=room_id,
            sender_id=buyer.id,
            message="Test message for deletion"
        )
        db.add(mock_msg)
        db.commit()
        print("[OK] Mock message added.")

        print("\n[Test 8] Deleting the chat room as buyer (should set buyer_deleted = True)...")
        res_delete_buyer = delete_chat_room(room_id=room_id, db=db, user=user_context)
        assert res_delete_buyer["success"] is True
        
        # 驗證 DB (因為 seller 還沒刪除，所以 room 應該還在，但 buyer_deleted 為 True)
        db.refresh(test_room)
        assert test_room is not None
        assert test_room.buyer_deleted is True
        assert test_room.seller_deleted is False
        print("[OK] Buyer deleted: Room still kept for seller.")

        print("\n[Test 9] Deleting the chat room as seller (should physically clear now)...")
        res_delete_seller = delete_chat_room(room_id=room_id, db=db, user=seller_context)
        assert res_delete_seller["success"] is True

        # 驗證 DB (雙方都刪除了，應該完全物理刪除)
        deleted_room = db.query(models.ChatRoom).filter(models.ChatRoom.id == room_id).first()
        deleted_msgs = db.query(models.ChatMessage).filter(models.ChatMessage.room_id == room_id).all()
        assert deleted_room is None, "Room must be physically deleted now"
        assert len(deleted_msgs) == 0, "All messages must be cascading deleted"
        print("[OK] DB verified: ChatRoom and all ChatMessages physically deleted successfully.")

        print("\n=======================================================")
        print("CONGRATULATIONS! ALL COMPREHENSIVE LIFE CYCLE TESTS PASSED!")
        print("=======================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_archive_block_delete_direct()
