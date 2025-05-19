import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
import pyttsx3
import os
import threading

APP_TITLE = "System TTS Offline"

class SystemTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("600x480") # زدت الارتفاع قليلاً لاستيعاب زر النسخ بشكل أفضل

        self.engine = pyttsx3.init()
        
        # --- واجهة المستخدم ---
        input_frame = ttk.LabelFrame(root, text="النص المراد تحويله")
        input_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10, font=("Arial", 12))
        self.text_area.pack(padx=5, pady=5, fill="both", expand=True)
        self.text_area.insert(tk.END, "مرحباً بك في تطبيق تحويل النص إلى كلام.")

        # --- إضافة قائمة السياق لمربع النص ---
        self.setup_text_area_context_menu()

        self.status_label = ttk.Label(root, text="الحالة: جاهز")
        # .pack() سيتم لاحقاً

        self.system_voices = self.find_system_voices()
        self.selected_voice_id = tk.StringVar()
        self.voice_rate = tk.IntVar(value=self.engine.getProperty('rate'))
        self.voice_volume = tk.DoubleVar(value=self.engine.getProperty('volume'))
        
        settings_frame = ttk.LabelFrame(root, text="إعدادات الصوت")
        settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(settings_frame, text="اختر الصوت:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.voice_dropdown = ttk.Combobox(settings_frame, textvariable=self.selected_voice_id,
                                           values=[v['name'] for v in self.system_voices],
                                           state="readonly", width=40)
        if self.system_voices:
            self.voice_dropdown.current(0)
            # self.set_selected_voice() # سيتم استدعاؤه من on_voice_change أو بشكل صريح
        self.voice_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.voice_dropdown.bind("<<ComboboxSelected>>", self.on_voice_change)

        ttk.Label(settings_frame, text="سرعة الكلام:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.rate_scale = ttk.Scale(settings_frame, from_=50, to=300, variable=self.voice_rate,
                                    orient=tk.HORIZONTAL, command=self.on_settings_change)
        self.rate_scale.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.rate_label = ttk.Label(settings_frame, textvariable=self.voice_rate)
        self.rate_label.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(settings_frame, text="مستوى الصوت:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.volume_scale = ttk.Scale(settings_frame, from_=0.0, to=1.0, variable=self.voice_volume,
                                     orient=tk.HORIZONTAL, command=self.on_settings_change)
        self.volume_scale.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.volume_percent_label_var = tk.StringVar()
        self.volume_percent_label = ttk.Label(settings_frame, textvariable=self.volume_percent_label_var)
        self.volume_percent_label.grid(row=2, column=2, padx=5, pady=5)

        settings_frame.columnconfigure(1, weight=1)

        control_frame = ttk.Frame(root)
        control_frame.pack(padx=10, pady=(5, 10), fill="x")

        self.speak_button = ttk.Button(control_frame, text="🔊 تحدث", command=self.speak_text_threaded)
        self.speak_button.pack(side=tk.LEFT, padx=(0, 5))

        self.save_button = ttk.Button(control_frame, text="💾 حفظ كـ WAV", command=self.save_audio_threaded)
        self.save_button.pack(side=tk.LEFT, padx=(0,5))

        # --- زر نسخ النص ---
        self.copy_button = ttk.Button(control_frame, text="📝 نسخ النص", command=self.copy_all_text_from_area)
        self.copy_button.pack(side=tk.LEFT)
        
        self.status_label.pack(pady=(0, 5))

        # استدعاء بعد تهيئة كل عناصر الواجهة لضمان أن status_label موجود
        if self.system_voices:
            self.set_selected_voice() 
        self.update_volume_label() # للتأكد من عرض النسبة المئوية لمستوى الصوت عند البدء
        self.on_settings_change() # لتطبيق القيم الأولية للمحرك

    def setup_text_area_context_menu(self):
        """إنشاء قائمة السياق لمربع النص."""
        self.text_area_context_menu = tk.Menu(self.root, tearoff=0)
        self.text_area_context_menu.add_command(label="قص", command=self.cut_text_from_area)
        self.text_area_context_menu.add_command(label="نسخ", command=self.copy_text_from_area_context)
        self.text_area_context_menu.add_command(label="لصق", command=self.paste_text_to_area)
        self.text_area_context_menu.add_separator()
        self.text_area_context_menu.add_command(label="تحديد الكل", command=self.select_all_text_in_area)


        self.text_area.bind("<Button-3>", self.show_text_area_context_menu) # <Button-3> للزر الأيمن

    def show_text_area_context_menu(self, event):
        """إظهار قائمة السياق في موقع الفأرة."""
        # تفعيل/تعطيل الخيارات بناءً على حالة التحديد والحافظة
        try:
            self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_area_context_menu.entryconfig("قص", state=tk.NORMAL)
            self.text_area_context_menu.entryconfig("نسخ", state=tk.NORMAL)
        except tk.TclError: # لا يوجد تحديد
            self.text_area_context_menu.entryconfig("قص", state=tk.DISABLED)
            self.text_area_context_menu.entryconfig("نسخ", state=tk.DISABLED) # أو يمكن نسخ الكل

        try:
            self.root.clipboard_get()
            self.text_area_context_menu.entryconfig("لصق", state=tk.NORMAL)
        except tk.TclError: # الحافظة فارغة
            self.text_area_context_menu.entryconfig("لصق", state=tk.DISABLED)

        self.text_area_context_menu.tk_popup(event.x_root, event.y_root)

    def cut_text_from_area(self):
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.text_area.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.status_label.config(text="الحالة: تم قص النص إلى الحافظة.")
        except tk.TclError:
            self.status_label.config(text="الحالة: لا يوجد نص محدد لقصه.")


    def copy_text_from_area_context(self):
        """نسخ النص المحدد من مربع النص (يستخدم بواسطة قائمة السياق)."""
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_label.config(text="الحالة: تم نسخ النص المحدد إلى الحافظة.")
        except tk.TclError:
            # إذا لم يكن هناك تحديد، يمكننا اختيار نسخ كل النص أو لا شيء
            # سأجعلها لا تفعل شيئاً إذا لم يكن هناك تحديد، لأن المستخدم اختار "نسخ" من قائمة السياق
            # التي يفترض أنها تعمل على التحديد. إذا أراد نسخ الكل، يستخدم الزر المخصص.
            # أو يمكننا تغيير هذا السلوك لنسخ الكل:
            # all_text = self.text_area.get("1.0", tk.END).strip()
            # if all_text:
            #     self.root.clipboard_clear()
            #     self.root.clipboard_append(all_text)
            #     self.status_label.config(text="الحالة: تم نسخ كل النص إلى الحافظة (لا يوجد تحديد).")
            # else:
            #     self.status_label.config(text="الحالة: لا يوجد نص لنسخه.")
            self.status_label.config(text="الحالة: لا يوجد نص محدد لنسخه.")


    def paste_text_to_area(self):
        try:
            text_to_paste = self.root.clipboard_get()
            # إذا كان هناك نص محدد، احذفه أولاً ثم الصق
            if self.text_area.tag_ranges(tk.SEL):
                self.text_area.delete(tk.SEL_FIRST, tk.SEL_LAST)
            
            # الحصول على موضع المؤشر الحالي
            insert_position = self.text_area.index(tk.INSERT)
            self.text_area.insert(insert_position, text_to_paste)
            self.status_label.config(text="الحالة: تم لصق النص من الحافظة.")
        except tk.TclError:
            self.status_label.config(text="الحالة: الحافظة فارغة أو تحتوي على بيانات غير نصية.")

    def select_all_text_in_area(self):
        self.text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.text_area.mark_set(tk.INSERT, "1.0")
        self.text_area.see(tk.INSERT)
        self.status_label.config(text="الحالة: تم تحديد كل النص.")


    def copy_all_text_from_area(self):
        """نسخ كل النص من مربع النص إلى الحافظة (يستخدم بواسطة الزر)."""
        all_text = self.text_area.get("1.0", tk.END).strip()
        if all_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(all_text)
            self.status_label.config(text="الحالة: تم نسخ كل النص إلى الحافظة.")
            messagebox.showinfo("تم النسخ", "تم نسخ النص بالكامل إلى الحافظة.")
        else:
            self.status_label.config(text="الحالة: لا يوجد نص لنسخه.")
            messagebox.showwarning("تنبيه", "لا يوجد نص في المربع لنسخه.")

    def update_volume_label(self, event=None):
        self.volume_percent_label_var.set(f"{int(self.voice_volume.get() * 100)}%")

    def find_system_voices(self):
        voices_props = []
        try:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                voices_props.append({'id': voice.id, 'name': voice.name, 'lang': voice.languages})
        except Exception as e:
            # في حالة فشل تهيئة pyttsx3 بشكل كامل (مثلاً على أنظمة لا تدعمها مباشرة)
            print(f"خطأ أثناء البحث عن الأصوات: {e}")
            # لا نعرض messagebox هنا مباشرة لأن الواجهة الرئيسية قد لا تكون جاهزة بالكامل
        return voices_props

    def set_selected_voice(self):
        if not hasattr(self, 'status_label'):
            print("تحذير: status_label غير مهيأ عند استدعاء set_selected_voice")
            return

        selected_voice_name = self.selected_voice_id.get()
        if not selected_voice_name: # قد يحدث هذا إذا كانت قائمة الأصوات فارغة
            if self.system_voices: # إذا كانت هناك أصوات ولكن لم يتم تحديد شيء (نادر)
                 self.status_label.config(text="الحالة: لم يتم اختيار صوت.")
            # إذا لم تكن هناك أصوات من الأساس، فسيتم التعامل مع هذا في نهاية __main__
            return

        voice_id_to_set = None
        for voice_info in self.system_voices:
            if voice_info['name'] == selected_voice_name:
                voice_id_to_set = voice_info['id']
                break
        
        if voice_id_to_set:
            try:
                self.engine.setProperty('voice', voice_id_to_set)
                self.status_label.config(text=f"الحالة: الصوت '{selected_voice_name}' محدد.")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل في تحديد الصوت: {e}")
                self.status_label.config(text="الحالة: خطأ في تحديد الصوت.")
        else:
            self.status_label.config(text=f"الحالة: لم يتم العثور على تعريف الصوت لـ {selected_voice_name}")

    def on_voice_change(self, event=None):
        self.set_selected_voice()
        # قد نرغب في تحديث الإعدادات الأخرى أيضاً إذا كان الصوت الجديد يتطلب ذلك
        # self.on_settings_change() 

    def on_settings_change(self, event=None):
        try:
            # التأكد من تهيئة المحرك قبل محاولة تعيين الخصائص
            if not self.engine._inLoop: # تحايل بسيط للتأكد أن المحرك ليس مشغولاً
                self.engine.setProperty('rate', self.voice_rate.get())
                self.engine.setProperty('volume', self.voice_volume.get())
            self.update_volume_label() 
            # لا نغير الحالة هنا دائماً، فقط عند تغيير فعلي من المستخدم
            # self.status_label.config(text="الحالة: تم تحديث الإعدادات.")
        except RuntimeError as e:
            # RuntimeError: run loop already started
            # هذا يعني أن المحرك مشغول، لا يمكن تغيير الخصائص الآن.
            # يمكن تأجيل التغيير أو إبلاغ المستخدم
            print(f"تحذير: لا يمكن تغيير إعدادات الصوت أثناء التشغيل: {e}")
            # قد نحتاج إلى آلية لتطبيق التغييرات بعد انتهاء التشغيل الحالي
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تحديث الإعدادات: {e}")
            self.status_label.config(text="الحالة: خطأ في تحديث الإعدادات.")

    def _process_audio(self, text, save_path=None):
        if not text.strip():
            messagebox.showwarning("تنبيه", "الرجاء إدخال نص ليتم تحويله.")
            self.status_label.config(text="الحالة: جاهز.") # إعادة الحالة
            return False

        self.status_label.config(text="الحالة: جاري معالجة الصوت...")
        self.speak_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED) # تعطيل زر النسخ أيضاً
        self.root.update_idletasks()

        try:
            # تطبيق الإعدادات الحالية قبل التشغيل
            self.engine.setProperty('rate', self.voice_rate.get())
            self.engine.setProperty('volume', self.voice_volume.get())
            current_selected_voice_name = self.selected_voice_id.get()
            voice_id_to_set = None
            for voice_info in self.system_voices:
                if voice_info['name'] == current_selected_voice_name:
                    voice_id_to_set = voice_info['id']
                    break
            if voice_id_to_set:
                 self.engine.setProperty('voice', voice_id_to_set)
            # else: # حالة عدم وجود صوت أو خطأ في الاختيار تم التعامل معها

            if save_path:
                self.engine.save_to_file(text, save_path)
                self.engine.runAndWait() 
                self.status_label.config(text=f"الحالة: تم حفظ الصوت في {os.path.basename(save_path)}")
            else:
                self.engine.say(text)
                self.engine.runAndWait()
                self.status_label.config(text="الحالة: انتهى التشغيل.")
            return True
        except Exception as e:
            messagebox.showerror("خطأ في المعالجة", f"حدث خطأ: {e}")
            self.status_label.config(text="الحالة: خطأ في المعالجة.")
            return False
        finally:
            self.speak_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.copy_button.config(state=tk.NORMAL) # إعادة تفعيل زر النسخ
            self.root.update_idletasks()

    def speak_text_threaded(self):
        text_to_speak = self.text_area.get("1.0", tk.END).strip()
        # التأكد من عدم وجود عملية تشغيل أخرى
        if self.engine._inLoop:
            messagebox.showinfo("مشغول", "المحرك الصوتي مشغول حالياً. الرجاء الانتظار.")
            return
        threading.Thread(target=self._process_audio, args=(text_to_speak,), daemon=True).start()

    def save_audio_threaded(self):
        text_to_save = self.text_area.get("1.0", tk.END).strip()
        if not text_to_save:
            messagebox.showwarning("تنبيه", "الرجاء إدخال نص ليتم تحويله وحفظه.")
            return

        if self.engine._inLoop:
            messagebox.showinfo("مشغول", "المحرك الصوتي مشغول حالياً. الرجاء الانتظار.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".wav", 
            filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")], # MP3 قد يتطلب مكتبة إضافية مثل pydub و ffmpeg
            title="حفظ الملف الصوتي"
        )
        if not save_path:
            return
        
        # التحقق من أن الامتداد هو WAV إذا كان pyttsx3 يحفظ WAV فقط افتراضياً
        # إذا أردت دعم MP3، ستحتاج لتحويل الملف بعد حفظه كـ WAV
        if not save_path.lower().endswith(".wav"):
            # يمكنك إما إجبار المستخدم على wav أو محاولة تحويله لاحقاً
            # حالياً، pyttsx3 يحفظ كـ wav افتراضياً، لذا سنلتزم به
             messagebox.showwarning("تنبيه الامتداد", "سيتم حفظ الملف بامتداد .wav. إذا اخترت .mp3، قد لا يعمل الحفظ بشكل صحيح مباشرةً.")
             # يمكنك إضافة منطق تحويل هنا إذا أردت دعم mp3 بشكل كامل


        threading.Thread(target=self._process_audio, args=(text_to_save, save_path), daemon=True).start()


if __name__ == "__main__":
    try:
        import pyttsx3
    except ImportError:
        print("مكتبة pyttsx3 غير مثبتة. جاري محاولة التثبيت...")
        # ملاحظة: pypiwin32 قد لا تكون مطلوبة دائماً أو قد تكون مثبتة كجزء من pywin32
        # من الأفضل تثبيت pywin32 إذا كان هناك مشاكل على ويندوز
        cmd_to_run = "pip install pyttsx3"
        if os.name == 'nt': # إذا كان نظام التشغيل ويندوز
            cmd_to_run += " pywin32"
        
        if os.system(cmd_to_run) == 0: 
            print(f"تم تثبيت pyttsx3 (و pywin32 إذا لزم الأمر). يرجى إعادة تشغيل التطبيق.")
        else:
            print(f"فشل تثبيت pyttsx3. يرجى تثبيتها يدوياً: {cmd_to_run}")
        exit()

    root = tk.Tk()
    app = SystemTTSApp(root)
    
    if not app.system_voices:
        messagebox.showwarning("لا توجد أصوات", "لم يتم العثور على أي أصوات TTS مثبتة على النظام. قد لا يعمل التطبيق بشكل صحيح أو قد لا تظهر أي أصوات للاختيار.")
        if hasattr(app, 'voice_dropdown'):
            app.voice_dropdown.config(state=tk.DISABLED)
            app.voice_dropdown.set("لا توجد أصوات متاحة") # رسالة أوضح
        if hasattr(app, 'speak_button'):
            app.speak_button.config(state=tk.DISABLED)
        if hasattr(app, 'save_button'):
            app.save_button.config(state=tk.DISABLED)
    else:
        # إذا كانت هناك أصوات، تأكد من أن القائمة المنسدلة ليست فارغة
        if not app.voice_dropdown.get() and app.system_voices:
            app.voice_dropdown.current(0) # اختر الأول كافتراضي
            app.on_voice_change() # قم بتطبيق هذا الاختيار

    root.mainloop()