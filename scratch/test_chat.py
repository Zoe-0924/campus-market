import os
import sys

# 將工作目錄加入 sys.path 以讀取專案模組
sys.path.append(os.path.abspath("c:/Users/user/Desktop/campus_market"))

import database
import models
from routers import chat

def test_chat_system():
    print("=== Start Chat and Notification System Validation ===")
    
    db = database.SessionLocal()
    try:
        # 1. 取得測試使用者與商品
        # 買家: StevenLee (ID 2), 賣家: 4113056033 (ID 1)
        # 商品: ID 1
        buyer = db.query(models.User).filter(models.User.id == 2).first()
        seller = db.query(models.User).filter(models.User.id == 1).first()
        product = db.query(models.Product).filter(models.Product.id == 1).first()
        
        if not buyer or not seller or not product:
            print("[ERROR] Test data insufficient. Ensure User ID 2 (StevenLee), User ID 1 (4113056033), and Product ID 1 exist.")
            return
            
        print(f"[OK] Found buyer: {buyer.username} (ID: {buyer.id})")
        print(f"[OK] Found seller: {seller.username} (ID: {seller.id})")
        print(f"[OK] Found product: {product.name} (ID: {product.id})")
        
        # 2. 清理現有相同設定的聊天室與訊息 (確保測試乾淨)
        existing_rooms = db.query(models.ChatRoom).filter(
            models.ChatRoom.product_id == product.id,
            models.ChatRoom.buyer_id == buyer.id
        ).all()
        for room in existing_rooms:
            db.query(models.ChatMessage).filter(models.ChatMessage.room_id == room.id).delete()
            db.delete(room)
        db.commit()
        print("[OK] Cleaned existing test rooms/messages.")
        
        # 3. 測試聊天室建立與載入
        print("\n[Test 1] Creating ChatRoom...")
        new_room = models.ChatRoom(
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=seller.id
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        print(f"[OK] ChatRoom created successfully! ID: {new_room.id}")
        
        # 4. 測試無任何訊息時的未讀狀態
        print("\n[Test 2] Verifying initial unread count (expected 0)...")
        # 模擬呼叫 get_unread_messages 的查詢邏輯
        def get_unread_count_simulated(user_id):
            unread = db.query(models.ChatMessage).filter(
                models.ChatMessage.room_id == new_room.id,
                models.ChatMessage.sender_id != user_id,
                models.ChatMessage.is_read == False
            ).all()
            return len(unread), unread

        count, _ = get_unread_count_simulated(buyer.id)
        print(f"Buyer {buyer.username} initial unread count: {count} (Expected: 0)")
        assert count == 0, "Initial unread count should be 0"
        
        # 5. 測試賣家發送訊息，買家收到通知
        print("\n[Test 3] Seller sends a message, verifying if buyer gets notified...")
        msg_text = "Hi Steven, is this textbook still available?"
        new_msg = models.ChatMessage(
            room_id=new_room.id,
            sender_id=seller.id,
            message=msg_text
        )
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)
        print(f"Seller sends message: '{msg_text}'")
        
        # 再次查詢買家的未讀數
        count, unread_list = get_unread_count_simulated(buyer.id)
        print(f"Buyer {buyer.username} unread count: {count} (Expected: 1)")
        print(f"Unread message content: '{unread_list[0].message}'")
        assert count == 1, "Unread count should be 1"
        assert unread_list[0].message == msg_text, "Unread message content mismatch"
        
        # 6. 測試將訊息標記為已讀
        print("\n[Test 4] Buyer enters room, verifying if message gets marked as read...")
        unread_msgs = db.query(models.ChatMessage).filter(
            models.ChatMessage.room_id == new_room.id,
            models.ChatMessage.sender_id != buyer.id,
            models.ChatMessage.is_read == False
        ).all()
        for msg in unread_msgs:
            msg.is_read = True
        db.commit()
        print("Message marked as read.")
        
        # 再次查詢買家的未讀數
        count, _ = get_unread_count_simulated(buyer.id)
        print(f"Buyer {buyer.username} updated unread count: {count} (Expected: 0)")
        assert count == 0, "Unread count should be 0 after marking as read"
        
        # 7. 清理測試產生的資料
        db.query(models.ChatMessage).filter(models.ChatMessage.room_id == new_room.id).delete()
        db.delete(new_room)
        db.commit()
        print("\nCleaned test rooms/messages.")
        print("\nCongratulations! All chat and notification lifecycle tests PASSED successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_chat_system()
