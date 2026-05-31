(function () {
    const storageKey = "campusMarketCart";
    const toast = document.querySelector("[data-toast]");
    const searchInput = document.querySelector("[data-search-input]");
    const searchForm = document.querySelector("[data-search-form]");
    const cartCount = document.querySelector("[data-cart-count]");
    const cartLists = [
        document.querySelector("[data-cart-list]"),
        document.querySelector("[data-cart-list-drawer]"),
    ].filter(Boolean);

    const readCart = () => {
        try {
            const items = JSON.parse(localStorage.getItem(storageKey) || "[]");
            const seen = new Set();
            const uniqueItems = items.filter((item) => {
                const key = item.id || item.name;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
            if (uniqueItems.length !== items.length) writeCart(uniqueItems);
            return uniqueItems;
        } catch (_) {
            return [];
        }
    };

    const writeCart = (items) => {
        localStorage.setItem(storageKey, JSON.stringify(items));
    };

    const showToast = (message) => {
        if (!toast) return;
        toast.textContent = message;
        toast.hidden = false;
        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => {
            toast.hidden = true;
        }, 1800);
    };

    const renderCart = () => {
        const items = readCart();
        if (cartCount) cartCount.textContent = String(items.length);
        cartLists.forEach((list) => {
            list.innerHTML = "";
            if (!items.length) {
                const empty = document.createElement("div");
                empty.className = "cart-item";
                empty.textContent = "還沒有加入商品。";
                list.append(empty);
                return;
            }
            items.forEach((item) => {
                const row = document.createElement("div");
                row.className = "cart-item";
                const label = document.createElement("span");
                label.textContent = `${item.name} · NT$ ${item.price}`;
                const remove = document.createElement("button");
                remove.className = "remove-cart-button";
                remove.type = "button";
                remove.dataset.removeCart = item.id || item.name;
                remove.textContent = "移除";
                row.append(label, remove);
                list.append(row);
            });
        });
    };

    const openDrawer = (name) => {
        document.querySelectorAll("[data-drawer]").forEach((drawer) => {
            drawer.hidden = drawer.dataset.drawer !== name;
        });
    };

    document.querySelectorAll("[data-open-drawer]").forEach((button) => {
        button.addEventListener("click", () => openDrawer(button.dataset.openDrawer));
    });

    document.querySelectorAll("[data-close-drawer]").forEach((button) => {
        button.addEventListener("click", () => {
            const drawer = button.closest("[data-drawer]");
            if (drawer) drawer.hidden = true;
        });
    });

    cartLists.forEach((list) => {
        list.addEventListener("click", (event) => {
            const button = event.target.closest("[data-remove-cart]");
            if (!button) return;
            const key = button.dataset.removeCart;
            const items = readCart().filter((item) => (item.id || item.name) !== key);
            writeCart(items);
            renderCart();
            showToast("已從待看清單移除。");
        });
    });

    document.querySelectorAll("[data-focus-search]").forEach((button) => {
        button.addEventListener("click", () => {
            searchInput?.focus();
            showToast("搜尋列已準備好。");
        });
    });

    document.querySelectorAll("[data-search-chip]").forEach((chip) => {
        chip.addEventListener("click", () => {
            if (!searchInput) return;
            searchInput.value = chip.dataset.searchChip || "";
            searchInput.focus();
            showToast(`已填入「${searchInput.value}」`);
        });
    });

    document.querySelectorAll("[data-add-cart]").forEach((button) => {
        button.addEventListener("click", () => {
            const card = button.closest("[data-product-card]");
            if (!card) return;
            const items = readCart();
            const id = card.dataset.productId;
            const name = card.dataset.productName;
            if (items.some((item) => item.id === id || item.name === name)) {
                showToast("這個商品已經在待看清單了。");
                return;
            }
            items.push({
                id,
                name,
                price: card.dataset.productPrice,
            });
            writeCart(items);
            renderCart();
            showToast("已加入待看清單。");
        });
    });

    // 拖曳橫向滾動分類軌道（滑鼠拖曳；手機觸控交由瀏覽器原生處理）並支援跑馬燈與無限循環
    document.querySelectorAll("[data-drag-scroll]").forEach((track) => {
        let isDragging = false;
        let startX = 0;
        let startScrollLeft = 0;
        let dragDistance = 0;
        let preventClick = false;
        let lastInteractionTime = 0;
        let animationFrameId = null;
        let isProgrammaticScroll = false;
        let currentFloatScroll = 0;
        let lastTime = performance.now();
        const pixelsPerSecond = 80; // 加快每秒滾動像素 (約 80px)，速度明顯且更順暢

        // 確保 DOM 渲染並套用 CSS 後再進行初始化計算
        setTimeout(() => {
            const originalChildren = Array.from(track.children);
            const originalLength = originalChildren.length;
            if (originalLength === 0) return;

            // 1. 無限循環複製：複製兩份子元素，形成 [Set A (原)][Set B (複製 1)][Set C (複製 2)]
            for (let i = 0; i < 2; i++) {
                originalChildren.forEach((child) => {
                    const clone = child.cloneNode(true);
                    track.appendChild(clone);
                });
            }

            // 確保 track 擁有 relative 屬性以準確計算 offsetLeft
            track.style.position = "relative";

            // 計算一個完整集合的滾動寬度 (利用 Set B 第一個元素的 offsetLeft 減去 Set A 第一個元素)
            const singleSetWidth = track.children[originalLength].offsetLeft - track.children[0].offsetLeft;

            // 2. 初始化滾動到中間的 Set B 區間，讓使用者左右滑動都有足夠內容
            isProgrammaticScroll = true;
            track.scrollLeft = singleSetWidth;
            isProgrammaticScroll = false;
            currentFloatScroll = singleSetWidth; // 同步浮點數

            // 3. 監聽滾動事件以觸發無感包裹 (Seamless Loop)
            track.addEventListener("scroll", () => {
                const currentScroll = track.scrollLeft;
                // 當滾動到右邊邊界 (Set C) 時，無感跳回 Set B 同樣位置
                if (currentScroll >= singleSetWidth * 2) {
                    isProgrammaticScroll = true;
                    track.scrollLeft = currentScroll - singleSetWidth;
                    isProgrammaticScroll = false;
                    currentFloatScroll = track.scrollLeft; // 同步浮點數
                }
                // 當滾動到左邊邊界 (Set A) 時，無感跳回 Set B 同樣位置
                else if (currentScroll < singleSetWidth) {
                    isProgrammaticScroll = true;
                    track.scrollLeft = currentScroll + singleSetWidth;
                    isProgrammaticScroll = false;
                    currentFloatScroll = track.scrollLeft; // 同步浮點數
                }
            });

            // 4. 跑馬燈自動滾動功能
            function step(timestamp) {
                const now = Date.now();
                const time = timestamp || performance.now();
                const dt = (time - lastTime) / 1000;
                lastTime = time;

                // 限制單次最大 dt (0.1秒)，防止分頁切換回前台時瞬間大跳躍
                const safeDt = Math.min(dt, 0.1);

                // 檢查是否處於懸停狀態
                const isHovered = track.matches(":hover");
                // 如果正處於：拖曳中、滑鼠懸停、或最近 1.0 秒內有觸控互動，則暫停跑馬燈
                const isUserInteracting = isDragging || isHovered || (now - lastInteractionTime < 1000);

                if (!isUserInteracting) {
                    isProgrammaticScroll = true;
                    currentFloatScroll += pixelsPerSecond * safeDt;
                    track.scrollLeft = Math.round(currentFloatScroll);
                    isProgrammaticScroll = false;
                } else {
                    // 使用者手動拖曳/滑動時，同步浮點數為目前最新整數位置
                    currentFloatScroll = track.scrollLeft;
                }
                animationFrameId = requestAnimationFrame(step);
            }
            lastTime = performance.now();
            animationFrameId = requestAnimationFrame(step);
        }, 100);

        // 5. 觸控事件監聽 (用於手機版滑動暫停，放開時立即恢復)
        track.addEventListener("touchstart", () => {
            lastInteractionTime = Date.now();
        }, { passive: true });

        track.addEventListener("touchmove", () => {
            lastInteractionTime = Date.now();
        }, { passive: true });

        track.addEventListener("touchend", () => {
            // 觸控結束後，保持暫停 600 毫秒以讓慣性滾動結束，然後恢復跑馬燈
            lastInteractionTime = Date.now() - 400; 
        }, { passive: true });

        let lastPageX = 0; // 用於計算每影格的相對滑鼠位移

        // 6. 滑鼠拖曳滾動功能
        track.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return; // 只允許滑鼠左鍵
            isDragging = true;
            lastInteractionTime = Date.now();
            startX = e.pageX;
            lastPageX = e.pageX;
            startScrollLeft = track.scrollLeft;
            dragDistance = 0;
            preventClick = false;
            track.classList.add("is-dragging");
        });

        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            // 如果滑動過程中發現滑鼠左鍵已經放開（例如在視窗外放開），安全釋放拖曳狀態
            if (e.buttons === 0) {
                isDragging = false;
                track.classList.remove("is-dragging");
                dragDistance = 0;
                lastInteractionTime = 0; // 立即恢復跑馬燈
                return;
            }
            lastInteractionTime = Date.now();
            
            const dx = e.pageX - lastPageX; // 相對前一次移動的距離
            lastPageX = e.pageX;            // 更新最後滑鼠座標
            
            dragDistance += Math.abs(dx);
            
            // 採用相對位移滾動，如此即使背景的 scroll 事件因為無限循環而重設了 scrollLeft，也不會造成數值衝突抖動
            track.scrollLeft -= dx;
        });

        document.addEventListener("mouseup", () => {
            if (!isDragging) return;
            isDragging = false;
            track.classList.remove("is-dragging");
            lastInteractionTime = 0; // 釋放拖曳，立即恢復跑馬燈
            // 如果總移動距離大於 10px，則判定為拖曳，阻止點擊事件觸發
            if (dragDistance > 10) {
                preventClick = true;
                setTimeout(() => {
                    preventClick = false;
                }, 50);
            }
            dragDistance = 0;
        });

        // 阻止瀏覽器預設的連結與圖片拖曳行為 (拖曳卡住的主因)
        track.addEventListener("dragstart", (e) => {
            e.preventDefault();
        });

        // 拖曳後防止連結被點擊觸發跳轉
        track.addEventListener("click", (e) => {
            if (preventClick) {
                e.preventDefault();
                e.stopImmediatePropagation();
                preventClick = false;
            }
        }, true);

        // 7. 監聽瀏覽器回到上一頁 (bfcache) 的還原事件
        window.addEventListener("pageshow", () => {
            lastInteractionTime = 0;
            lastTime = performance.now(); // 重置動畫時間戳
            currentFloatScroll = track.scrollLeft; // 同步位置
        });
    });

    document.querySelectorAll("[data-card-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll("[data-card-filter]").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");

            const filter = button.dataset.cardFilter;
            document.querySelectorAll("[data-product-card]").forEach((card, index) => {
                const tags = (card.dataset.productTags || "").toLowerCase();
                const price = Number(card.dataset.productPrice || 0);
                let show = true;
                if (filter === "new") show = tags.includes("新") || tags.includes("九成");
                if (filter === "used") show = tags.includes("二手") || tags.includes("良品") || index % 2 === 0;
                if (filter === "sale") show = tags.includes("急售") || tags.includes("可議價") || price <= 300;
                card.hidden = !show;
            });
        });
    });

    searchForm?.addEventListener("submit", () => {
        showToast("正在幫你搜尋校園好物。");
    });

    // 即時聊天新訊息通知系統 (Polling Notification System)
    const initNotificationSystem = () => {
        let lastUnreadCount = 0;
        let notifiedMessages = {}; // room_id -> last_notified_msg
        let audioCtx = null;

        // 初始化與啟動音訊，解除並預熱瀏覽器自動播放限制
        const unlockAudio = () => {
            try {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                if (audioCtx && audioCtx.state === "suspended") {
                    audioCtx.resume();
                }
            } catch (_) {}
        };
        // 隨時監聽使用者點擊與按鍵，確保 AudioContext 在瀏覽器中處於啟動狀態
        document.addEventListener("click", unlockAudio);
        document.addEventListener("keydown", unlockAudio);

        // 建立一個美觀的、可點擊的浮動通知 Toast
        const showFloatingNotification = (sender, message, roomId) => {
            // 如果當前頁面就是該聊天室，不重複彈出通知
            if (window.location.pathname.startsWith("/chat")) {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get("room_id") == roomId) return;
            }

            const container = document.createElement("div");
            container.className = "custom-floating-toast";
            container.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: #ffe359;
                color: #242424;
                border: 3px solid #242424;
                border-radius: 12px;
                padding: 16px 20px;
                box-shadow: 6px 6px 0 #242424;
                z-index: 99999;
                display: flex;
                flex-direction: column;
                gap: 6px;
                cursor: pointer;
                max-width: 320px;
                transition: transform 0.2s, box-shadow 0.2s;
                font-family: inherit;
            `;

            container.innerHTML = `
                <div style="font-weight: 900; font-size: 1rem; display: flex; align-items: center; gap: 8px;">
                    💬 新訊息來自: <span style="text-decoration: underline;">${sender}</span>
                </div>
                <div style="font-size: 0.9rem; font-weight: 800; color: #555; word-break: break-all; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                    ${message}
                </div>
            `;

            container.addEventListener("mouseenter", () => {
                container.style.transform = "translate(-2px, -2px)";
                container.style.boxShadow = "8px 8px 0 #242424";
            });
            container.addEventListener("mouseleave", () => {
                container.style.transform = "none";
                container.style.boxShadow = "6px 6px 0 #242424";
            });

            container.addEventListener("click", () => {
                window.location.href = `/chat?room_id=${roomId}`;
            });

            document.body.appendChild(container);

            // 播放通知音效 (Web Audio API 產生一個乾淨的「叮」聲，並配合預熱解鎖的 audioCtx)
            try {
                unlockAudio();
                const ctx = audioCtx;
                if (ctx) {
                    if (ctx.state === "suspended") {
                        ctx.resume();
                    }
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "sine";
                    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
                    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.08); // A5
                    gain.gain.setValueAtTime(0.08, ctx.currentTime);
                    gain.gain.linearRampToValueAtTime(0.0001, ctx.currentTime + 0.35);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.35);
                }
            } catch (_) {}

            // 6秒後自動消失
            setTimeout(() => {
                container.style.opacity = "0";
                container.style.transform = "translateY(20px)";
                container.style.transition = "opacity 0.4s, transform 0.4s";
                setTimeout(() => container.remove(), 400);
            }, 6000);
        };

        const checkUnread = async () => {
            try {
                const response = await fetch("/chat/api/unread");
                if (!response.ok) return;
                const data = await response.json();

                const count = data.unread_count;

                // 1. 更新所有「我的訊息」導覽列連結中的 Badge
                const chatLinks = document.querySelectorAll('a[href="/chat"], a[href="/chat/"]');
                chatLinks.forEach(link => {
                    // 確保父級元素是 relative 定位，防止絕對定位的 badge 飛到頁面外面！
                    link.style.position = "relative";
                    
                    let badge = link.querySelector(".chat-unread-badge");
                    if (count > 0) {
                        if (!badge) {
                            badge = document.createElement("span");
                            badge.className = "badge-count chat-unread-badge";
                            badge.style.cssText = "margin-left: 6px; background: #ff4757; color: white; border: 2px solid #242424; box-shadow: 1px 1px 0 #242424; padding: 1px 6px; font-size: 0.75rem; border-radius: 50%; font-weight: 900;";
                            link.appendChild(badge);
                        }
                        badge.textContent = count;
                    } else if (badge) {
                        badge.remove();
                    }
                });

                // 2. 檢查新訊息以觸發 Toast 通知
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(notif => {
                        const roomKey = notif.room_id;
                        // 如果這條訊息還沒有被通知過
                        if (notifiedMessages[roomKey] !== notif.message) {
                            const isInitialLoad = Object.keys(notifiedMessages).length === 0 && lastUnreadCount === 0;
                            notifiedMessages[roomKey] = notif.message;
                            
                            // 第一次加載時不彈窗，避免頁面重整時把舊的未讀訊息通通彈出來
                            if (!isInitialLoad) {
                                showFloatingNotification(notif.sender, notif.message, notif.room_id);
                            }
                        }
                    });
                } else {
                    notifiedMessages = {};
                }

                lastUnreadCount = count;
            } catch (err) {
                // 忽略非登入狀態的錯誤
            }
        };

        // 立即檢查一次，隨後每 4 秒輪詢一次
        checkUnread();
        setInterval(checkUnread, 4000);
    };

    // 啟動通知系統
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initNotificationSystem);
    } else {
        initNotificationSystem();
    }

    renderCart();
})();
