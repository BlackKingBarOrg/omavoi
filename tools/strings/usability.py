"""User-facing labels shared by the usability changes.

New entries carry all eight interface languages. Existing translations are
preserved unless an override is explicitly supplied.
"""
LANGS = ('en', 'zh', 'th', 'de', 'fr', 'es', 'ja', 'vi')
NEW = {
'modes.ai.none': ('No rewrite', '不改写', 'ไม่เขียนใหม่', 'Nicht überarbeiten', 'Pas de réécriture', 'Sin reescritura', '書き直さない', 'Không viết lại'),
'modes.ai.none.sub': ('Typed as the speech model heard it, after the rules above. The fastest.', '识别结果经过上面的规则整理后直接输出，最快。', 'พิมพ์ตามที่โมเดลเสียงได้ยิน หลังผ่านกฎด้านบน เร็วที่สุด', 'So getippt, wie das Sprachmodell es gehört hat, nach den Regeln oben. Am schnellsten.', 'Tapé tel que le modèle vocal l’a entendu, après les règles ci-dessus. Le plus rapide.', 'Se escribe tal como lo oyó el modelo de voz, tras las reglas de arriba. Lo más rápido.', '音声モデルが聞き取った内容を、上のルールで整えてそのまま入力します。最速です。', 'Gõ đúng như mô hình giọng nói nghe được, sau các quy tắc ở trên. Nhanh nhất.'),
'modes.ai.local.sub': ('Runs on this computer; your words do not leave it.', '在这台电脑上运行，文字不会离开本机。', 'ทำงานบนคอมพิวเตอร์เครื่องนี้ ข้อความไม่ออกไปนอกเครื่อง', 'Läuft auf diesem Computer; deine Worte verlassen ihn nicht.', 'Tourne sur cet ordinateur ; vos mots ne le quittent pas.', 'Se ejecuta en este equipo; tus palabras no salen de él.', 'このコンピューターで動作し、テキストは外に出ません。', 'Chạy trên máy tính này; lời bạn không rời khỏi máy.'),
'modes.ai.chain': ('This mode rewrites in %1 steps, one after another.', '这个模式按顺序改写 %1 次。', 'โหมดนี้เขียนใหม่ %1 ขั้น ทีละขั้น', 'Dieser Modus überarbeitet in %1 Schritten nacheinander.', 'Ce mode réécrit en %1 étapes, l’une après l’autre.', 'Este modo reescribe en %1 pasos, uno tras otro.', 'このモードは %1 段階で順に書き直します。', 'Chế độ này viết lại qua %1 bước, lần lượt.'),
'modes.ai.none.confirm': ('The rewrite instructions in “%1” are ones you wrote. No rewrite deletes them; choosing an AI again brings back the built-in ones.', '“%1”的改写要求是你自己写的。选“不改写”会把它删掉；之后再选 AI，会换回系统自带的改写要求。', 'คำสั่งแก้ไขใน “%1” เป็นของที่คุณเขียนเอง การเลือก “ไม่เขียนใหม่” จะลบคำสั่งนี้ และเมื่อเลือก AI อีกครั้งจะได้คำสั่งที่มีมาในตัวแทน', 'Die Überarbeitungsanweisungen in „%1“ hast du selbst geschrieben. „Nicht überarbeiten“ löscht sie; wählst du danach wieder eine KI, kommen die mitgelieferten zurück.', 'Les instructions de réécriture de « %1 » sont les vôtres. « Pas de réécriture » les supprime ; si vous choisissez à nouveau une IA, ce sont celles fournies d’origine qui reviennent.', 'Las instrucciones de reescritura de «%1» las escribiste tú. «Sin reescritura» las elimina; si vuelves a elegir una IA, vuelven las que trae de serie.', '「%1」の書き換え指示はあなたが書いたものです。「書き直さない」を選ぶと削除され、あとで AI を選び直すと組み込みの指示に戻ります。', 'Hướng dẫn viết lại trong “%1” là do bạn tự viết. “Không viết lại” sẽ xóa chúng; khi chọn lại AI, hướng dẫn có sẵn sẽ được dùng thay thế.'),
'modes.ai.none.drop': ('Delete the instructions', '删除改写要求', 'ลบคำสั่งแก้ไข', 'Anweisungen löschen', 'Supprimer les instructions', 'Eliminar las instrucciones', '指示を削除', 'Xóa hướng dẫn'),
'modes.sum.noai': ('no AI', '不经过 AI','ไม่ผ่าน AI', 'ohne KI', 'sans IA', 'sin IA', 'AI なし', 'không qua AI'),
'models.k.current': ('used by the current mode, %1', '当前模式「%1」在用', 'โหมดปัจจุบัน %1 ใช้อยู่', 'vom aktuellen Modus %1 genutzt', 'utilisé par le mode actuel, %1', 'lo usa el modo actual, %1', '現在のモード「%1」が使用中', 'chế độ hiện tại %1 đang dùng'),
'models.k.recent': ('usually %1 s here', '本机一般约 %1 秒', 'ปกติราว %1 วินาทีบนเครื่องนี้', 'hier meist etwa %1 s', 'ici en général environ %1 s', 'aquí suele tardar unos %1 s', 'この端末では通常約 %1 秒', 'trên máy này thường khoảng %1 giây'),
'first.m.qwen': ('Recommended: the most accurate in Chinese and English, and the fastest. 30 languages.', '推荐：中文和英文识别最准，速度也最快，支持 30 种语言。', 'แนะนำ: แม่นที่สุดทั้งภาษาจีนและภาษาอังกฤษ และเร็วที่สุด รองรับ 30 ภาษา', 'Empfohlen: am genauesten für Chinesisch und Englisch und am schnellsten. 30 Sprachen.', 'Recommandé : le plus précis en chinois et en anglais, et le plus rapide. 30 langues.', 'Recomendado: el más preciso en chino e inglés, y el más rápido. 30 idiomas.', '推奨：中国語と英語で最も正確で、最も速い。30 言語に対応。', 'Đề xuất: chính xác nhất với tiếng Trung và tiếng Anh, và nhanh nhất. 30 ngôn ngữ.'),
'feedback.saving': ('Saving…', '正在保存……', 'กำลังบันทึก…', 'Wird gespeichert…', 'Enregistrement…', 'Guardando…', '保存中…', 'Đang lưu…'),
'feedback.saved': ('Saved and applied.', '已保存并生效。', 'บันทึกและใช้แล้ว', 'Gespeichert und angewendet.', 'Enregistré et appliqué.', 'Guardado y aplicado.', '保存して適用しました。', 'Đã lưu và áp dụng.'),
'feedback.failed': ('The change could not be completed. Your previous settings may still apply; see details.', '修改未完成，部分设置可能仍保持原样。请查看详细原因。', 'เปลี่ยนแปลงไม่สำเร็จ การตั้งค่าเดิมอาจยังมีผล ดูรายละเอียด', 'Änderung nicht abgeschlossen. Frühere Einstellungen können noch gelten; siehe Details.', 'Modification incomplète. Les anciens réglages peuvent encore s’appliquer ; voir les détails.', 'No se completó el cambio. Puede que sigan vigentes los ajustes anteriores; consulta los detalles.', '変更を完了できませんでした。以前の設定が有効な場合があります。詳細を確認してください。', 'Chưa hoàn tất thay đổi. Cài đặt cũ có thể vẫn có hiệu lực; hãy xem chi tiết.'),
'feedback.pending': ('Saved. Start the speech service to apply the change.', '已保存，启动语音服务后生效。', 'บันทึกแล้ว เริ่มบริการเสียงเพื่อใช้การเปลี่ยนแปลง', 'Gespeichert. Zum Anwenden den Sprachdienst starten.', 'Enregistré. Démarrez le service vocal pour appliquer.', 'Guardado. Inicia el servicio de voz para aplicarlo.', '保存しました。音声サービスを起動すると適用されます。', 'Đã lưu. Khởi động dịch vụ giọng nói để áp dụng.'),
'feedback.restart': ('Saved. Restart the speech service to apply the recording settings.', '已保存，重启语音服务后应用新的录音设置。', 'บันทึกแล้ว เริ่มบริการเสียงใหม่เพื่อใช้การตั้งค่าการอัดเสียงใหม่', 'Gespeichert. Den Sprachdienst neu starten, um die Aufnahmeeinstellungen anzuwenden.', 'Enregistré. Redémarrez le service vocal pour appliquer les réglages audio.', 'Guardado. Reinicia el servicio de voz para aplicar los ajustes de grabación.', '保存しました。音声サービスを再起動すると録音設定が適用されます。', 'Đã lưu. Khởi động lại dịch vụ giọng nói để áp dụng cài đặt ghi âm.'),
'feedback.details': ('Show details', '查看详细原因', 'ดูรายละเอียด', 'Details anzeigen', 'Voir les détails', 'Ver detalles', '詳細を表示', 'Xem chi tiết'),
'mic.title': ('Microphone', '麦克风', 'ไมโครโฟน', 'Mikrofon', 'Microphone', 'Micrófono', 'マイク', 'Micrô'),
'mic.note': ('Choose the microphone used for dictation. Changing it requires a speech service restart.', '选择听写使用的麦克风。更换后需重启语音服务。', 'เลือกไมโครโฟนสำหรับป้อนตามเสียง เปลี่ยนแล้วต้องเริ่มบริการเสียงใหม่', 'Mikrofon zum Diktieren auswählen. Ein Wechsel erfordert einen Neustart des Sprachdienstes.', 'Choisissez le microphone de dictée. Un changement nécessite de redémarrer le service vocal.', 'Elige el micrófono de dictado. Cambiarlo requiere reiniciar el servicio de voz.', '音声入力に使うマイクを選びます。変更後は音声サービスの再起動が必要です。', 'Chọn micrô dùng để nhập giọng nói. Cần khởi động lại dịch vụ sau khi đổi.'),
'mic.default': ('Use system microphone', '跟随系统麦克风', 'ใช้ไมโครโฟนของระบบ', 'Systemmikrofon verwenden', 'Microphone du système', 'Usar micrófono del sistema', 'システムのマイクを使用', 'Dùng micrô hệ thống'),
'mic.unavailable': ('not connected', '未连接', 'ไม่ได้เชื่อมต่อ', 'nicht verbunden', 'non connecté', 'sin conexión', '未接続', 'chưa kết nối'),
'mic.refresh': ('Refresh', '刷新列表', 'รีเฟรช', 'Aktualisieren', 'Actualiser', 'Actualizar', '更新', 'Làm mới'),
'mic.test': ('Test microphone', '试一下麦克风', 'ทดสอบไมโครโฟน', 'Mikrofon testen', 'Tester le microphone', 'Probar micrófono', 'マイクをテスト', 'Thử micrô'),
'mic.testing': ('Speak for 3 seconds, then listen to the playback…', '请说话 3 秒，随后会自动回放……', 'พูด 3 วินาที แล้วฟังเสียงที่บันทึก…', '3 Sekunden sprechen, dann die Wiedergabe anhören…', 'Parlez pendant 3 secondes, puis écoutez…', 'Habla durante 3 segundos y escucha la reproducción…', '3秒間話してください。その後、自動で再生します…', 'Nói trong 3 giây, rồi nghe phát lại…'),
'mic.testnote': ('Records 3 seconds and plays them back locally. The test recording is deleted afterwards.', '录制 3 秒并在本机回放，测试后自动删除录音。', 'บันทึก 3 วินาทีและเล่นบนเครื่อง แล้วลบเสียงทดสอบ', 'Nimmt 3 Sekunden auf und spielt sie lokal ab. Die Testaufnahme wird danach gelöscht.', 'Enregistre 3 secondes et les lit localement. L’enregistrement est ensuite supprimé.', 'Graba 3 segundos y los reproduce localmente. Después se borra la grabación de prueba.', '3秒録音してこの端末で再生し、テスト後に削除します。', 'Ghi 3 giây rồi phát lại trên máy. Bản ghi thử được xóa sau đó.'),
'mic.done': ('Test complete. Could you hear yourself clearly?', '测试完成。请确认回放中能清楚听到自己的声音。', 'ทดสอบเสร็จแล้ว ตรวจสอบว่าได้ยินเสียงชัดเจน', 'Test abgeschlossen. War die Stimme deutlich zu hören?', 'Test terminé. Votre voix était-elle claire ?', 'Prueba terminada. ¿Se oía tu voz claramente?', 'テストが完了しました。声がはっきり聞こえるか確認してください。', 'Thử xong. Hãy kiểm tra xem giọng của bạn có rõ không.'),
'mic.quiet': ('The recording was very quiet. Check the microphone, input volume, and distance.', '录音音量偏小。请检查麦克风、输入音量和说话距离。', 'เสียงเบามาก ตรวจสอบไมโครโฟน ระดับเสียงเข้า และระยะห่าง', 'Die Aufnahme war sehr leise. Mikrofon, Eingangslautstärke und Abstand prüfen.', 'L’enregistrement était très faible. Vérifiez le microphone, le volume d’entrée et la distance.', 'La grabación fue muy baja. Revisa el micrófono, el volumen de entrada y la distancia.', '録音音量が小さいようです。マイク、入力音量、距離を確認してください。', 'Âm lượng ghi rất nhỏ. Kiểm tra micrô, âm lượng đầu vào và khoảng cách.'),
'mic.failed': ('Could not record or play back. Check the selected microphone and system audio settings.', '无法录音或回放。请检查所选麦克风和系统声音设置。', 'บันทึกหรือเล่นเสียงไม่ได้ ตรวจสอบไมโครโฟนและการตั้งค่าเสียงของระบบ', 'Aufnahme oder Wiedergabe fehlgeschlagen. Mikrofon und System-Audioeinstellungen prüfen.', 'Échec de l’enregistrement ou de la lecture. Vérifiez le microphone et les réglages audio du système.', 'No se pudo grabar o reproducir. Revisa el micrófono y los ajustes de sonido del sistema.', '録音または再生ができませんでした。マイクとシステムの音声設定を確認してください。', 'Không thể ghi hoặc phát lại. Kiểm tra micrô và cài đặt âm thanh hệ thống.'),
'history.save': ('Save history', '保存听写历史', 'บันทึกประวัติ', 'Verlauf speichern', 'Conserver l’historique', 'Guardar historial', '履歴を保存', 'Lưu lịch sử'),
'history.savenote': ('Turning this off stops saving new text and recordings. Existing history is kept until you delete it.', '关闭后不再保存新的文字和录音；已有历史仍会保留，可在下方删除。', 'ปิดแล้วจะไม่บันทึกข้อความและเสียงใหม่ ประวัติเดิมยังคงอยู่จนกว่าจะลบ', 'Ausgeschaltet werden keine neuen Texte oder Aufnahmen gespeichert. Bestehender Verlauf bleibt bis zum Löschen erhalten.', 'Désactivé : aucun nouveau texte ni enregistrement n’est conservé. L’historique existant reste jusqu’à sa suppression.', 'Al desactivarlo no se guardan nuevos textos ni grabaciones. El historial existente se conserva hasta borrarlo.', 'オフにすると新しいテキストと録音を保存しません。既存の履歴は削除するまで残ります。', 'Tắt sẽ ngừng lưu văn bản và bản ghi mới. Lịch sử cũ vẫn còn cho đến khi bạn xóa.'),
'history.textcount': ('Keep recent text entries', '保留最近的文字记录', 'เก็บข้อความล่าสุด', 'Neueste Texteinträge behalten', 'Textes récents à conserver', 'Conservar textos recientes', '保持する最近のテキスト数', 'Giữ văn bản gần nhất'),
'history.noaudio': ('Stop saving new recordings', '不再保存新录音', 'หยุดบันทึกเสียงใหม่', 'Keine neuen Aufnahmen speichern', 'Ne plus conserver de nouveaux enregistrements', 'No guardar nuevas grabaciones', '新しい録音を保存しない', 'Ngừng lưu bản ghi mới'),
'word.selectedmodes': ('Selected modes', '指定模式', 'โหมดที่เลือก', 'Ausgewählte Modi', 'Modes choisis', 'Modos seleccionados', '指定したモード', 'Chế độ đã chọn'),
'word.selectmode': ('Select at least one mode, or choose All modes.', '请至少选择一个模式，或选择“所有模式”。', 'เลือกอย่างน้อยหนึ่งโหมด หรือเลือกทุกโหมด', 'Mindestens einen Modus oder Alle Modi auswählen.', 'Choisissez au moins un mode, ou Tous les modes.', 'Elige al menos un modo o Todos los modos.', '1つ以上のモード、または「すべてのモード」を選んでください。', 'Chọn ít nhất một chế độ hoặc Tất cả chế độ.'),
'word.previewresult': ('After correction', '纠正后', 'หลังแก้ไข', 'Nach der Korrektur', 'Après correction', 'Tras la corrección', '修正後', 'Sau khi sửa'),
'key.right': ('Right %1', '右 %1', '%1 ขวา', '%1 rechts', '%1 droit', '%1 derecho', '右 %1', '%1 phải'),
'key.left': ('Left %1', '左 %1', '%1 ซ้าย', '%1 links', '%1 gauche', '%1 izquierdo', '左 %1', '%1 trái'),
'mode.name.default': ('Everyday dictation', '日常听写', 'ป้อนตามเสียงทั่วไป', 'Alltagsdiktat', 'Dictée courante', 'Dictado diario', '通常の音声入力', 'Nhập giọng nói hằng ngày'),
'mode.name.code': ('Code editor', '代码编辑', 'เขียนโค้ด', 'Code-Editor', 'Éditeur de code', 'Editor de código', 'コード編集', 'Soạn mã'),
'mode.name.prose': ('Polished writing', '文字润色', 'ขัดเกลาข้อความ', 'Text überarbeiten', 'Texte soigné', 'Mejorar redacción', '文章の推敲', 'Trau chuốt văn bản'),
'mode.name.terminal': ('Terminal input', '终端输入', 'ป้อนในเทอร์มินัล', 'Terminaleingabe', 'Saisie dans le terminal', 'Entrada de terminal', '端末入力', 'Nhập vào terminal'),
'modes.instructions': ('Rewrite instructions', '改写要求', 'คำสั่งเขียนใหม่', 'Anweisungen zum Überarbeiten', 'Instructions de réécriture', 'Instrucciones de reescritura', '書き換えの指示', 'Hướng dẫn viết lại'),
'modes.copy': ('Copy', '复制', 'คัดลอก', 'Kopieren', 'Copier', 'Copiar', '複製', 'Sao chép'),
'modes.deleteconfirm': ('Delete “%1”, including its rewrite instructions and settings?', '删除“%1”以及其中的改写要求和设置？', 'ลบ “%1” รวมคำสั่งแก้ไขและการตั้งค่าหรือไม่', '„%1“ mit allen Überarbeitungsanweisungen und Einstellungen löschen?', 'Supprimer « %1 », ses instructions et ses réglages ?', '¿Eliminar «%1», sus instrucciones de reescritura y ajustes?', '「%1」の書き換え指示と設定も含めて削除しますか？', 'Xóa “%1” cùng hướng dẫn viết lại và cài đặt?'),
'modes.pickapp': ('Choose an open application…', '选择已打开的应用……', 'เลือกแอปที่เปิดอยู่…', 'Geöffnete Anwendung auswählen…', 'Choisir une application ouverte…', 'Elegir una aplicación abierta…', '起動中のアプリを選択…', 'Chọn ứng dụng đang mở…'),
}
NEW.update({
'api.enable': ('Save and enable', '保存并启用', 'บันทึกและเปิดใช้', 'Speichern und aktivieren', 'Enregistrer et activer', 'Guardar y activar', '保存して有効にする', 'Lưu và bật'),
'api.invalid': ('Enter an http:// or https:// API address and a model name.', '请填写以 http:// 或 https:// 开头的 API 地址，以及模型名称。', 'ใส่ที่อยู่ API ที่ขึ้นต้นด้วย http:// หรือ https:// และชื่อโมเดล', 'Eine API-Adresse mit http:// oder https:// und einen Modellnamen eingeben.', 'Saisissez une adresse API http:// ou https:// et un nom de modèle.', 'Introduce una dirección API http:// o https:// y un nombre de modelo.', 'http:// または https:// で始まる API アドレスとモデル名を入力してください。', 'Nhập địa chỉ API bắt đầu bằng http:// hoặc https:// và tên mô hình.'),
'api.savenote': ('Save the form before testing the connection. A connection test retrieves the model list; it does not run recognition or rewriting.', '保存配置后可测试连接。连接测试只获取模型列表，不会运行识别或改写。', 'บันทึกก่อนทดสอบ การทดสอบดึงรายชื่อโมเดล ไม่รู้จำเสียงหรือเขียนใหม่', 'Vor dem Verbindungstest speichern. Der Test ruft die Modellliste ab, führt aber keine Erkennung oder Überarbeitung aus.', 'Enregistrez avant le test. Il récupère la liste des modèles sans reconnaissance ni réécriture.', 'Guarda antes de probar. La prueba obtiene la lista de modelos, sin reconocimiento ni reescritura.', '保存後に接続をテストできます。モデル一覧のみ取得し、認識や書き換えは実行しません。', 'Lưu trước khi kiểm tra kết nối. Kiểm tra chỉ lấy danh sách mô hình, không nhận dạng hay viết lại.'),
'api.search': ('Search models…', '搜索模型……', 'ค้นหาโมเดล…', 'Modelle suchen…', 'Rechercher un modèle…', 'Buscar modelos…', 'モデルを検索…', 'Tìm mô hình…'),
'edit.savefirst': ('Save or revert the draft before removing a step.', '请先保存或还原草稿，再移除步骤。', 'บันทึกหรือคืนร่างก่อนลบขั้นตอน', 'Vor dem Entfernen den Entwurf speichern oder zurücksetzen.', 'Enregistrez ou annulez le brouillon avant de retirer une étape.', 'Guarda o revierte el borrador antes de eliminar un paso.', '手順を削除する前に下書きを保存するか元に戻してください。', 'Lưu hoặc hoàn tác bản nháp trước khi xóa bước.'),
'edit.draftkept': ('Unsaved instructions are kept while you switch modes. Return to the edited field to save or revert them.', '有尚未保存的要求。切换模式会保留草稿，请回到编辑处保存或还原。', 'เก็บร่างเมื่อสลับโหมด กลับไปบันทึกหรือคืนค่าที่ช่องเดิม', 'Ungespeicherte Anweisungen bleiben beim Moduswechsel erhalten. Zum Speichern oder Zurücksetzen zum Feld zurückkehren.', 'Le brouillon reste lors du changement de mode. Revenez au champ pour enregistrer ou annuler.', 'El borrador se conserva al cambiar de modo. Vuelve al campo para guardarlo o revertirlo.', 'モードを切り替えても下書きは保持されます。編集欄に戻って保存するか元に戻してください。', 'Bản nháp được giữ khi đổi chế độ. Quay lại ô đã sửa để lưu hoặc hoàn tác.'),
})

NEW.update({
'hist.showing': ('Showing %1 recent entries', '显示最近 %1 条记录', 'แสดง %1 รายการล่าสุด', '%1 neueste Einträge', '%1 entrées récentes affichées', 'Mostrando %1 entradas recientes', '最近の %1 件を表示', 'Hiển thị %1 mục gần nhất'),
'hist.more': ('Load more', '加载更多', 'โหลดเพิ่ม', 'Mehr laden', 'Charger plus', 'Cargar más', 'さらに読み込む', 'Tải thêm'),
'hist.noaudio': ('This recording was not saved or has been cleared.', '这条录音未保存或已被清理。', 'ไม่ได้บันทึกเสียงนี้หรือถูกล้างแล้ว', 'Diese Aufnahme wurde nicht gespeichert oder bereits gelöscht.', 'Cet enregistrement n’a pas été conservé ou a été supprimé.', 'Esta grabación no se guardó o ya se borró.', 'この録音は保存されていないか、削除されています。', 'Bản ghi này chưa được lưu hoặc đã bị xóa.'),
'setup.commands': ('View technical commands', '查看具体命令', 'ดูคำสั่งทางเทคนิค', 'Technische Befehle anzeigen', 'Voir les commandes techniques', 'Ver comandos técnicos', '実行コマンドを表示', 'Xem lệnh kỹ thuật'),
})

NEW.update({
'models.downloadsize': ('Download', '下载大小', 'ขนาดดาวน์โหลด', 'Download', 'Téléchargement', 'Descarga', 'ダウンロード', 'Tải về'),
'models.default': ('Default', '默认模型', 'ค่าเริ่มต้น', 'Standard', 'Par défaut', 'Predeterminado', '既定', 'Mặc định'),
'models.downloaded': ('Downloaded', '已下载', 'ดาวน์โหลดแล้ว', 'Heruntergeladen', 'Téléchargé', 'Descargado', 'ダウンロード済み', 'Đã tải'),
'models.recommended': ('Recommended', '推荐', 'แนะนำ', 'Empfohlen', 'Recommandé', 'Recomendado', '推奨', 'Đề xuất'),
'models.localfiles': ('Show or hide downloaded/local models', '展开或收起本机模型', 'แสดงหรือซ่อนโมเดลในเครื่อง', 'Lokale Modelle ein-/ausblenden', 'Afficher ou masquer les modèles locaux', 'Mostrar u ocultar modelos locales', 'ローカルモデルを表示・非表示', 'Hiện hoặc ẩn mô hình cục bộ'),
'unit.seconds': ('seconds', '秒', 'วินาที', 'Sekunden', 'secondes', 'segundos', '秒', 'giây'),
'unit.minutes': ('minutes', '分钟', 'นาที', 'Minuten', 'minutes', 'minutos', '分', 'phút'),
'set.preview': ('Size preview', '大小预览', 'ตัวอย่างขนาด', 'Größenvorschau', 'Aperçu de la taille', 'Vista previa del tamaño', 'サイズのプレビュー', 'Xem trước kích thước'),
})

# Wording improvements to the two languages audited together.
UPDATES = {
'set.key.rebind': ('Change shortcut', '更改快捷键'),
'set.key.press': ('Press the new shortcut · %1 seconds left', '请按下新快捷键 · 剩余 %1 秒'),
'set.key.check': ('Test shortcut', '检测快捷键'),
'set.key.ok': ('Shortcut ready · %1', '快捷键可用 · %1'),
'set.key.type': ('Key name, e.g. F9', '按键名称，如 F9'),
'set.behaviour': ('Recording style', '录音方式'),
'set.key.nogroup': ('Keyboard access is needed to use this shortcut.', '使用快捷键需要键盘访问权限。'),
'set.key.relogin': ('Restart with keyboard access to enable your shortcut.', '需要重新启动语音服务，让键盘访问权限生效。'),
'set.key.stopped': ('Start the speech service to enable your shortcut.', '语音服务未运行，启动后即可使用快捷键。'),
'set.key.fix.restart': ('Start speech service', '启动语音服务'),
'set.key.fix.regroup': ('Enable keyboard access', '启用键盘访问权限'),
'set.key.fix.group': ('Grant keyboard access', '授予键盘访问权限'),
'set.hotkeynote': ('This key still performs its original action. Avoid keys you normally use for typing.', '这个键原来的功能仍会触发，请避免选择常用打字键。'),
'set.hud.show': ('Show while recording', '录音时显示提示条'),
'set.keepup': ('Result display', '识别结果显示方式'),
'set.dwell.always': ('Show each result', '每次显示'),
'set.dwell.changed': ('Show longer after changes or warnings', '有改动或警告时延长显示'),
'set.dwell.never': ('Hide dictated text', '不显示识别文字'),
'set.hudnote': ('Results normally appear briefly. Changes or warnings keep them visible longer. Failure messages still appear when dictated text is hidden.', '普通结果短暂显示，有改动或警告时多显示一会儿。隐藏识别文字后，失败提示仍会显示。'),
'set.notifications': ('Notify about recording problems', '录音异常时通知我'),
'set.keepaudio': ('Keep recent recordings', '保留最近的录音'),
'set.historynote': ('0 stops saving new recordings; existing recordings are not deleted. Text retention is set separately above.', '设为 0 后不再保存新录音，已有录音不会被删除。文字记录按上方数量保留。'),
'set.clearhistory': ('Delete all text and recordings', '删除全部文字记录和录音'),
'set.clearnote': ('Deletes existing history and recordings. This cannot be undone.', '删除已有文字记录和录音，此操作无法撤销。'),
'set.preroll': ('Keep sound before the key', '保留按键前的声音'),
'set.tail': ('Keep sound after stopping', '结束后继续录制'),
'set.tailwhy': ('Continue briefly after recording ends, so the last word is not cut off.', '结束录音后再多录一小会儿，避免最后一个字被切掉。'),
'set.warnbelow': ('Low-volume warning threshold', '低音量提醒阈值'),
'set.maxtake': ('Maximum recording length', '单次录音最长时长'),
'set.restart': ('Restart speech service', '重启语音服务'),
'modes.newname': ('Name for a copy of %1', '复制“%1”，输入新名称'),
'modes.hiddenauto': ('The active application chooses the mode. Select a mode below to edit its applications and settings.', '按当前使用的应用自动切换。点击下方模式，可编辑它对应的应用和设置。'),
'modes.opens': ('Applications using this mode', '使用此模式的应用'),
'modes.classph': ('Or enter an app name or title keyword', '或输入应用标识、窗口标题关键词'),
'modes.matchhint': ('Matches application names or window titles. More specific matches win; unmatched windows use Everyday dictation.', '按应用标识或窗口标题匹配，较长的关键词优先；未匹配的应用使用“日常听写”。'),
'modes.nothing': ('No applications assigned yet', '尚未指定应用'),
'modes.langauto': ('Detect language automatically', '自动识别语言'),
'modes.script': ('Chinese output', '中文输出'),
'modes.script.none': ('Keep recognized characters', '保持识别结果'),
'modes.rulessub': ('Fixed text cleanup rules, without waiting for AI.', '按固定规则整理文字，无需等待 AI。'),
'modes.decoderhint': ('Recognition reference', '识别参考信息'),
'modes.prompthint': ('Topics or special terms for the voice model, %1, to listen for, not instructions for the AI. My dictionary is added automatically. One voice model serves every mode; change it on the Models tab.', '供语音模型 %1 参考的话题或专有名词，不是给 AI 的指令。「我的词典」会自动加入。语音模型所有模式共用，在「模型」页更换。', 'หัวข้อหรือคำเฉพาะให้โมเดลเสียง %1 ใช้อ้างอิง ไม่ใช่คำสั่งสำหรับ AI พจนานุกรมของฉัน จะถูกเพิ่มเอง ทุกโหมดใช้โมเดลเสียงตัวเดียวกัน เปลี่ยนได้ที่แท็บโมเดล', 'Themen oder Fachbegriffe, auf die das Erkennungsmodell %1 achten soll – keine Anweisungen an die KI. Mein Wörterbuch kommt von selbst dazu. Alle Modi nutzen ein Erkennungsmodell; gewechselt wird es im Tab Modelle.', 'Des sujets ou termes particuliers que le modèle vocal %1 doit reconnaître, pas des consignes pour l’IA. Mon dictionnaire est ajouté d’office. Un seul modèle vocal sert tous les modes ; il se change dans l’onglet Modèles.', 'Temas o términos especiales que el modelo de voz %1 debe reconocer, no instrucciones para la IA. Mi diccionario se añade solo. Un único modelo de voz sirve a todos los modos; se cambia en la pestaña Modelos.', '音声モデル %1 が聞き取りの参考にする話題や専門用語です。AI への指示ではありません。「自分の辞書」は自動で加わります。音声モデルは全モード共通で、「モデル」タブで変更します。', 'Chủ đề hoặc thuật ngữ để mô hình giọng nói %1 tham khảo khi nghe, không phải chỉ dẫn cho AI. Từ điển của tôi được tự thêm vào. Mọi chế độ dùng chung một mô hình giọng nói; đổi ở thẻ Mô hình.'),
'modes.inject.hint.auto': ('Choose a compatible way to enter text in the current application automatically.', '自动选择适合当前应用的文字输入方式。'),
'modes.inject.hint.type': ('Simulate typing into the current application.', '模拟键盘输入，将文字输入当前应用。'),
'modes.inject.hint.paste': ('Paste the text, then restore your clipboard. Some older applications require simulated typing instead.', '粘贴文字后恢复原剪贴板。部分旧应用会改用模拟键盘输入。'),
'word.another': ('Add another incorrect spelling', '再加一种错误写法'),
'word.hinthelp': ('Helps recognition but does not guarantee the spelling. Online services may receive this word along with the recording.', '提高识别概率，不保证每次写对。使用在线服务时，这个词可能随录音一起发送。'),
'word.case': ('Match this capitalization, e.g. JavaScript', '统一为这里的大小写，如 JavaScript'),
}

UPDATES.update({
'models.f.url': ('API address', 'API 服务地址'),
'models.f.key.place': ('Paste an API key; leave blank to keep the saved key', '粘贴 API 密钥；留空则保留已保存的密钥'),
'models.f.key.saved': ('API key saved.', 'API 密钥已保存。'),
'models.f.key.fromfile': ('Using your saved API key', '正在使用已保存的 API 密钥'),
'models.f.testok': ('Connected; retrieved %1 models.', '连接成功，已获取 %1 个模型。'),
'models.f.testfail': ('Could not retrieve models. Check the address and API key.', '无法获取模型列表。请检查服务地址和 API 密钥。'),
'models.e.vulkan': ('On this computer', '在这台电脑识别'),
'models.e.api': ('Online or self-hosted service', '在线或自建识别服务'),
'models.e.vulkan.sub': ('Recognize speech locally using the GPU or CPU. Recordings stay on this computer.', '在本机使用显卡或 CPU 识别，录音无需上传。'),
'models.k.agent': ('Your coding assistant', '已登录的编程助手'),
'models.k.api': ('Online AI service', '在线 AI 服务'),
'models.k.agent.sub': ('Uses the coding assistant selected in Omarchy. It starts afresh for every rewrite, so each takes several seconds; text is sent to its signed-in service, and no API key is needed.', '使用 Omarchy 中选择的编程助手。每次改写都要重新启动它，所以每次要好几秒；文字会发送至它登录的服务，无需另填 API 密钥。'),
'models.use': ('Set as default', '设为默认模型'),
'models.coldshort': ('Starts when needed', '首次使用时启动'),
'modes.addstep': ('+ Add another rewrite step', '+ 再加一步改写', '+ เพิ่มขั้นเขียนใหม่อีกขั้น', '+ Weiteren Überarbeitungsschritt hinzufügen', '+ Ajouter une autre étape de réécriture', '+ Añadir otro paso de reescritura', '+ 書き直しをもう 1 段階追加', '+ Thêm một bước viết lại nữa'),
'models.llmsub': ('Whether each one works here, and how fast it is. Which one a mode uses is chosen on the Modes page.', '这里显示每种方式能不能用、在本机有多快；每个模式用哪一种，在「模式」页里选。'),
'modes.llmsub': ('Whether this mode’s text goes through an AI before it is typed. If the AI fails, what was recognized is typed as it was.', '说完话后是否交给 AI 改写一遍。AI 出错时，照样输出识别结果。'),
'models.list.speech.sub': ('The one every mode hears through. Bigger is more accurate, smaller is faster; a download does not switch to it.', '所有模式共用这一个语音模型。越大越准，越小越快；下载后点「改用这个」才会换过去。', 'โมเดลเสียงตัวเดียวที่ทุกโหมดใช้ ยิ่งใหญ่ยิ่งแม่น ยิ่งเล็กยิ่งเร็ว ดาวน์โหลดแล้วต้องกด “ใช้ตัวนี้” จึงจะเปลี่ยน', 'Das eine Sprachmodell für alle Modi. Größer ist genauer, kleiner schneller; ein Download wechselt nicht von selbst – dafür „Dieses nutzen“.', 'Le modèle vocal que tous les modes utilisent. Plus gros, plus précis ; plus petit, plus rapide. Un téléchargement ne change rien avant « Utiliser celui-ci ».', 'El modelo de voz que usan todos los modos. Más grande es más preciso; más pequeño, más rápido. Descargarlo no lo activa: pulsa «Usar este».', 'すべてのモードが使う音声モデルです。大きいほど正確、小さいほど高速。ダウンロードしただけでは切り替わらず、「これを使う」で切り替えます。', 'Mô hình giọng nói mà mọi chế độ dùng chung. Lớn hơn thì chính xác hơn, nhỏ hơn thì nhanh hơn; tải xuống chưa đổi sang nó, hãy bấm “Dùng mô hình này”.'),
'models.list.llm.sub': ('Models for local AI rewriting. Set a default here, or choose a different model for an individual rewrite step.', '本地 AI 改写使用的模型。在这里设置默认模型，也可在某个改写步骤中单独选择。'),
})

UPDATES.update({
'up.dirty': ('The interface files have local edits, so automatic updates are paused. Back up and resolve those edits, then check again.', '界面文件有本地改动，已暂停自动更新。请先备份并处理这些改动，再重新检查。',
    'ไฟล์ส่วนติดต่อมีการแก้ไขในเครื่อง จึงพักการอัปเดตอัตโนมัติ สำรองและจัดการการแก้ไขก่อนตรวจสอบอีกครั้ง',
    'Die Oberflächendateien wurden lokal geändert. Automatische Updates sind pausiert. Änderungen sichern und bereinigen, dann erneut prüfen.',
    'Des fichiers de l’interface ont été modifiés localement. Les mises à jour automatiques sont suspendues. Sauvegardez et traitez ces modifications, puis vérifiez à nouveau.',
    'Hay cambios locales en los archivos de la interfaz. Las actualizaciones automáticas están pausadas. Guarda y resuelve esos cambios antes de volver a comprobar.',
    '画面のファイルがローカルで変更されているため、自動更新を停止しています。変更をバックアップして処理してから、再確認してください。',
    'Tệp giao diện có chỉnh sửa cục bộ nên tạm dừng cập nhật tự động. Sao lưu và xử lý các thay đổi, rồi kiểm tra lại.'),
'first.blurb': ('Recommended settings are selected. Adjust them if needed, then install.', '已选好推荐配置，可按需要调整，然后开始安装。'),
'first.m.light': ('Smaller download and lower memory use; recognition may be less accurate.', '下载较小、占用内存较少，识别准确率可能有所下降。'),
'first.m.turbo': ('Whisper, balancing quality and speed in 99 languages; for a language the recommended model does not cover.', 'whisper 中兼顾识别效果和速度的一个，支持 99 种语言；推荐模型不支持你的语言时选它。'),
'first.m.large': ('Larger download and slower recognition; includes a speech-versus-silence check.', '下载较大、识别较慢，支持检测录音是否包含说话声。'),
'first.hotkey.note': ('The key keeps its original function. Right Ctrl is recommended; Right Alt is used for typing on some keyboard layouts.', '这个键仍会触发原来的功能。推荐右 Ctrl；部分键盘布局会用右 Alt 输入字符。'),
'first.group.needed': ('Setup will request keyboard access so your shortcut can work immediately.', '安装时会请求键盘访问权限，完成后即可使用快捷键。'),
'up.current': ('Interface component is up to date', '界面组件已是最新'),
'up.behind': ('An interface update is available', '有可用的界面更新'),
'up.daemon.blind': ('The speech service version could not be compared. Update installs the matching service and restarts it.', '尚未确认语音服务是否为最新版本。更新会安装配套服务并重启。'),
'up.unknown': ('Automatic update checking is unavailable for this installation.', '当前安装方式不支持自动检查更新。'),
'up.noupstream': ('No update source is configured for this installation.', '当前安装尚未配置更新来源。'),
'modes.fallback': ('Other applications', '其他应用'),
'modes.longestwins': ('The most specific application or title match wins. Other applications use Everyday dictation.', '较长的应用标识或标题关键词优先匹配，其他应用使用“日常听写”。'),
})


# Changes in meaning, rather than tone, must reach every supported language.
SEMANTIC_TRANSLATIONS = {
    'set.historynote': (
        '0 หยุดบันทึกเสียงใหม่ แต่ไม่ลบเสียงเดิม จำนวนข้อความตั้งค่าแยกด้านบน',
        '0 stoppt das Speichern neuer Aufnahmen, löscht aber keine vorhandenen. Die Anzahl der Texteinträge wird oben separat eingestellt.',
        '0 arrête la conservation des nouveaux enregistrements sans supprimer les anciens. Le nombre de textes conservés se règle séparément ci-dessus.',
        '0 deja de guardar nuevas grabaciones sin borrar las existentes. La cantidad de textos se configura por separado arriba.',
        '0 にすると新しい録音を保存しません。既存の録音は削除されません。テキストの保存件数は上で別に設定します。',
        '0 ngừng lưu bản ghi âm mới, không xóa bản ghi cũ. Số văn bản lưu được đặt riêng ở trên.'),
    'set.dwell.changed': (
        'แสดงนานขึ้นเมื่อมีการแก้ไขหรือคำเตือน', 'Bei Änderungen oder Warnungen länger anzeigen',
        'Afficher plus longtemps après modification ou avertissement', 'Mostrar más tiempo si hay cambios o avisos',
        '変更や警告があるときは長く表示', 'Hiển thị lâu hơn khi có thay đổi hoặc cảnh báo'),
    'set.hudnote': (
        'ปกติแสดงผลสั้น ๆ หากมีการแก้ไขหรือคำเตือนจะแสดงนานขึ้น แม้ซ่อนข้อความยังแสดงข้อผิดพลาด',
        'Ergebnisse erscheinen kurz, bei Änderungen oder Warnungen länger. Fehlermeldungen bleiben auch bei ausgeblendetem Text sichtbar.',
        'Les résultats apparaissent brièvement, plus longtemps après modification ou avertissement. Les erreurs restent visibles même si le texte est masqué.',
        'Los resultados se muestran brevemente, más tiempo si hay cambios o avisos. Los errores siguen apareciendo aunque se oculte el texto.',
        '通常は結果を短時間表示し、変更や警告があるときは長く表示します。認識テキストを非表示にしてもエラーは表示されます。',
        'Kết quả hiện ngắn, lâu hơn khi có thay đổi hoặc cảnh báo. Lỗi vẫn hiển thị khi ẩn văn bản nhận dạng.'),
    'first.blurb': (
        'เลือกค่าที่แนะนำไว้แล้ว ปรับได้ตามต้องการแล้วเริ่มติดตั้ง',
        'Empfohlene Einstellungen sind ausgewählt. Bei Bedarf anpassen und dann installieren.',
        'Les réglages recommandés sont sélectionnés. Ajustez-les si besoin, puis installez.',
        'Los ajustes recomendados ya están seleccionados. Ajústalos si lo necesitas e instala.',
        '推奨設定を選択済みです。必要に応じて変更してからインストールしてください。',
        'Đã chọn cài đặt đề xuất. Điều chỉnh nếu cần, rồi cài đặt.'),
    'set.key.press': (
        'กดปุ่มลัดใหม่ · เหลือ %1 วินาที', 'Neue Tastenkombination drücken · noch %1 Sekunden',
        'Appuyez sur le nouveau raccourci · reste %1 secondes', 'Pulsa el nuevo atajo · quedan %1 segundos',
        '新しいショートカットを押してください · 残り %1 秒', 'Nhấn phím tắt mới · còn %1 giây'),
    'modes.newname': (
        'ชื่อสำเนาของ %1', 'Name für eine Kopie von %1', 'Nom de la copie de %1',
        'Nombre de la copia de %1', '%1 のコピー名', 'Tên bản sao của %1'),
    'models.use': (
        'ตั้งเป็นค่าเริ่มต้น', 'Als Standard festlegen', 'Définir par défaut', 'Usar por defecto', '既定に設定', 'Đặt làm mặc định'),
    # Saying how slow it is again, which the shorter wording had dropped.
    'models.k.agent.sub': (
        'ใช้ผู้ช่วยเขียนโค้ดที่เลือกไว้ใน Omarchy เริ่มใหม่ทุกครั้งที่เขียนใหม่ จึงใช้เวลาหลายวินาทีต่อครั้ง ข้อความจะถูกส่งไปยังบริการที่ล็อกอินไว้ ไม่ต้องใช้คีย์ API',
        'Nutzt den in Omarchy gewählten Coding-Assistenten. Er startet für jede Überarbeitung neu und braucht daher jedes Mal mehrere Sekunden; der Text geht an seinen angemeldeten Dienst, ein API-Schlüssel ist nicht nötig.',
        'Utilise l’assistant de code choisi dans Omarchy. Il redémarre à chaque réécriture, donc plusieurs secondes à chaque fois ; le texte part vers son service connecté, sans clé d’API.',
        'Usa el asistente de programación elegido en Omarchy. Arranca de nuevo en cada reescritura, así que tarda varios segundos cada vez; el texto va a su servicio con sesión iniciada y no hace falta clave de API.',
        'Omarchy で選んだコーディングアシスタントを使います。書き直しのたびに起動し直すため毎回数秒かかります。テキストはログイン先のサービスに送られ、API キーは不要です。',
        'Dùng trợ lý lập trình đã chọn trong Omarchy. Mỗi lần viết lại đều phải khởi động lại nên mất vài giây; văn bản được gửi tới dịch vụ đã đăng nhập, không cần khóa API.'),
    # Not a choice among three: each mode's step has its own, and the frame
    # marks the current mode's.
    'models.llmsub': (
        'แสดงว่าแต่ละแบบใช้ได้หรือไม่และเร็วแค่ไหนบนเครื่องนี้ โหมดไหนใช้แบบใดเลือกได้ที่หน้าโหมด',
        'Ob jede davon hier funktioniert und wie schnell sie ist. Welche ein Modus nutzt, wählst du auf der Seite Modi.',
        'Si chacune fonctionne ici, et à quelle vitesse. Celle qu’utilise un mode se choisit sur la page Modes.',
        'Si cada una funciona aquí y lo rápida que es. Cuál usa un modo se elige en la página Modos.',
        'それぞれがここで使えるか、どのくらい速いかを示します。モードごとにどれを使うかは「モード」ページで選びます。',
        'Mỗi cách có dùng được ở đây không và nhanh thế nào. Chế độ dùng cách nào thì chọn ở trang Chế độ.'),
    'modes.llmsub': (
        'ส่งข้อความของโหมดนี้ให้ AI เขียนใหม่ก่อนพิมพ์หรือไม่ ถ้า AI ผิดพลาด จะพิมพ์ผลที่ฟังได้ตามเดิม',
        'Ob der Text dieses Modus vor dem Tippen durch eine KI geht. Scheitert sie, wird das Erkannte unverändert getippt.',
        'Si le texte de ce mode passe par une IA avant d’être tapé. Si l’IA échoue, ce qui a été reconnu est tapé tel quel.',
        'Si el texto de este modo pasa por una IA antes de escribirse. Si la IA falla, se escribe lo reconocido tal cual.',
        '入力の前にこのモードのテキストを AI に書き直させるかどうか。AI が失敗したときは認識結果をそのまま入力します。',
        'Văn bản của chế độ này có qua AI trước khi gõ hay không. Nếu AI lỗi, kết quả nhận dạng được gõ nguyên như cũ.'),
    # No longer the default: every language must stop saying it is.
    'first.m.turbo': (
        'whisper ที่สมดุลระหว่างคุณภาพกับความเร็ว รองรับ 99 ภาษา เลือกเมื่อโมเดลที่แนะนำไม่รองรับภาษาของคุณ',
        'Whisper, ausgewogen zwischen Qualität und Tempo, 99 Sprachen; für eine Sprache, die das empfohlene Modell nicht abdeckt.',
        'Whisper, équilibré entre qualité et vitesse, 99 langues ; pour une langue que le modèle recommandé ne couvre pas.',
        'Whisper, equilibrado entre calidad y velocidad, 99 idiomas; para un idioma que el modelo recomendado no cubre.',
        'whisper の中で品質と速度のバランスが良いモデル。99 言語に対応。推奨モデルが対応しない言語のときに。',
        'Whisper cân bằng chất lượng và tốc độ, 99 ngôn ngữ; dùng khi mô hình đề xuất không hỗ trợ ngôn ngữ của bạn.'),
    'models.f.testok': (
        'เชื่อมต่อแล้ว ได้รับ %1 โมเดล', 'Verbunden; %1 Modelle abgerufen.',
        'Connecté ; %1 modèles récupérés.', 'Conectado; se obtuvieron %1 modelos.',
        '接続できました。%1 個のモデルを取得しました。', 'Đã kết nối; lấy được %1 mô hình.'),
}
for _key, _translations in SEMANTIC_TRANSLATIONS.items():
    UPDATES[_key] = (*UPDATES[_key], *_translations)


def apply(sections, extra):
    new = {}
    entries_by_key = {key: entries for _, entries in sections for key in entries}
    for key, values in UPDATES.items():
        entries = entries_by_key[key]
        old = entries[key]
        entries[key] = (*values[:2], values[2] if len(values) > 2 else old[2])
        if len(values) == len(LANGS):
            for index, lang in enumerate(LANGS[3:], 3):
                extra[lang][key] = values[index]
    for key, values in NEW.items():
        new[key] = values[:3]
        for index, lang in enumerate(LANGS[3:], 3):
            extra[lang][key] = values[index]
    sections.append(('usability', new))
