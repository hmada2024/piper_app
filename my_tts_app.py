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
        self.root.geometry("600x480") 

        self.engine = pyttsx3.init()
        
        # --- واجهة المستخدم ---
        input_frame = ttk.LabelFrame(root, text="النص المراد تحويله")
        input_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10, font=("Arial", 12))
        self.text_area.pack(padx=5, pady=5, fill="both", expand=True)
        self.text_area.insert(tk.END, "مرحباً بك في تطبيق تحويل النص إلى كلام.")

        self.setup_text_area_context_menu()

        self.status_label = ttk.Label(root, text="الحالة: جاهز")

        self.system_voices = self.find_system_voices()
        self.selected_voice_id = tk.StringVar()
        self.voice_rate = tk.IntVar(value=self.engine.getProperty('rate'))
        self.voice_volume = tk.DoubleVar(value=self.engine.getProperty('volume'))
        
        settings_frame = ttk.LabelFrame(root, text="إعدادات الصوت")
        settings_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(settings_frame, text="اختر الصوت:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.voice_dropdown = ttk.Combobox(settings_frame, textvariable=self.selected_voice_id,
                                           values=[v['name'] for v in self.system_voices],
                                           state="readonly", width=35) # قللت العرض قليلاً
        if self.system_voices:
            self.voice_dropdown.current(0)
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

        self.save_button = ttk.Button(control_frame, text="💾 حفظ", command=self.save_audio_threaded) # اختصرت النص
        self.save_button.pack(side=tk.LEFT, padx=(0,5))

        self.copy_button = ttk.Button(control_frame, text="📝 نسخ", command=self.copy_all_text_from_area) # اختصرت النص
        self.copy_button.pack(side=tk.LEFT, padx=(0,5))

        # --- زر لصق النص ---
        self.paste_button = ttk.Button(control_frame, text="📋 لصق", command=self.paste_text_to_area_button)
        self.paste_button.pack(side=tk.LEFT)
        
        self.status_label.pack(pady=(0, 5))

        if self.system_voices:
            self.set_selected_voice() 
        self.update_volume_label()
        self.on_settings_change()

    def setup_text_area_context_menu(self):
        self.text_area_context_menu = tk.Menu(self.root, tearoff=0)
        self.text_area_context_menu.add_command(label="قص", command=self.cut_text_from_area)
        self.text_area_context_menu.add_command(label="نسخ", command=self.copy_text_from_area_context)
        self.text_area_context_menu.add_command(label="لصق", command=self.paste_text_from_context) # دالة منفصلة لقائمة السياق
        self.text_area_context_menu.add_separator()
        self.text_area_context_menu.add_command(label="تحديد الكل", command=self.select_all_text_in_area)
        self.text_area.bind("<Button-3>", self.show_text_area_context_menu)

    def show_text_area_context_menu(self, event):
        try:
            self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text_area_context_menu.entryconfig("قص", state=tk.NORMAL)
            self.text_area_context_menu.entryconfig("نسخ", state=tk.NORMAL)
        except tk.TclError: 
            self.text_area_context_menu.entryconfig("قص", state=tk.DISABLED)
            self.text_area_context_menu.entryconfig("نسخ", state=tk.DISABLED)

        try:
            self.root.clipboard_get()
            self.text_area_context_menu.entryconfig("لصق", state=tk.NORMAL)
        except tk.TclError: 
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
        try:
            selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_label.config(text="الحالة: تم نسخ النص المحدد إلى الحافظة.")
        except tk.TclError:
            self.status_label.config(text="الحالة: لا يوجد نص محدد لنسخه.")

    def _perform_paste(self, from_button=False):
        """الدالة المشتركة لعملية اللصق."""
        try:
            text_to_paste = self.root.clipboard_get()
            
            # إذا كان هناك نص محدد، احذفه أولاً ثم الصق
            # هذا السلوك شائع للزر وللقائمة إذا لم يكن هناك مؤشر واضح
            if self.text_area.tag_ranges(tk.SEL):
                self.text_area.delete(tk.SEL_FIRST, tk.SEL_LAST)
            
            insert_position = self.text_area.index(tk.INSERT)
            self.text_area.insert(insert_position, text_to_paste)
            self.status_label.config(text="الحالة: تم لصق النص من الحافظة.")
            if from_button:
                 messagebox.showinfo("تم اللصق", "تم لصق النص من الحافظة بنجاح.")
        except tk.TclError:
            self.status_label.config(text="الحالة: الحافظة فارغة أو تحتوي على بيانات غير نصية.")
            if from_button:
                messagebox.showwarning("خطأ في اللصق", "الحافظة فارغة أو تحتوي على بيانات غير نصية.")

    def paste_text_from_context(self):
        """لصق النص (يستخدم بواسطة قائمة السياق)."""
        self._perform_paste(from_button=False) # لا تعرض messagebox من هنا

    def paste_text_to_area_button(self):
        """لصق النص (يستخدم بواسطة الزر)."""
        self._perform_paste(from_button=True) # اعرض messagebox من هنا

    def select_all_text_in_area(self):
        self.text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.text_area.mark_set(tk.INSERT, "1.0")
        self.text_area.see(tk.INSERT)
        self.status_label.config(text="الحالة: تم تحديد كل النص.")

    def copy_all_text_from_area(self):
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
            print(f"خطأ أثناء البحث عن الأصوات: {e}")
        return voices_props

    def set_selected_voice(self):
        if not hasattr(self, 'status_label'):
            print("تحذير: status_label غير مهيأ عند استدعاء set_selected_voice")
            return

        selected_voice_name = self.selected_voice_id.get()
        if not selected_voice_name:
            if self.system_voices:
                 self.status_label.config(text="الحالة: لم يتم اختيار صوت.")
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

    def on_settings_change(self, event=None):
        try:
            if not self.engine._inLoop:
                self.engine.setProperty('rate', self.voice_rate.get())
                self.engine.setProperty('volume', self.voice_volume.get())
            self.update_volume_label() 
        except RuntimeError as e:
            print(f"تحذير: لا يمكن تغيير إعدادات الصوت أثناء التشغيل: {e}")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تحديث الإعدادات: {e}")
            self.status_label.config(text="الحالة: خطأ في تحديث الإعدادات.")

    def _process_audio(self, text, save_path=None):
        if not text.strip():
            messagebox.showwarning("تنبيه", "الرجاء إدخال نص ليتم تحويله.")
            self.status_label.config(text="الحالة: جاهز.")
            return False

        self.status_label.config(text="الحالة: جاري معالجة الصوت...")
        self.speak_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
        self.paste_button.config(state=tk.DISABLED) # تعطيل زر اللصق أيضاً
        self.root.update_idletasks()

        try:
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
            self.copy_button.config(state=tk.NORMAL)
            self.paste_button.config(state=tk.NORMAL) # إعادة تفعيل زر اللصق
            self.root.update_idletasks()

    def speak_text_threaded(self):
        text_to_speak = self.text_area.get("1.0", tk.END).strip()
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
            filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")],
            title="حفظ الملف الصوتي"
        )
        if not save_path:
            return
        
        if not save_path.lower().endswith(".wav"):
             messagebox.showwarning("تنبيه الامتداد", "سيتم حفظ الملف بامتداد .wav. إذا اخترت .mp3، قد لا يعمل الحفظ بشكل صحيح مباشرةً مع pyttsx3.")

        threading.Thread(target=self._process_audio, args=(text_to_save, save_path), daemon=True).start()


if __name__ == "__main__":
    try:
        import pyttsx3
    except ImportError:
        print("مكتبة pyttsx3 غير مثبتة. جاري محاولة التثبيت...")
        cmd_to_run = "pip install pyttsx3"
        if os.name == 'nt':
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
            app.voice_dropdown.set("لا توجد أصوات متاحة")
        if hasattr(app, 'speak_button'):
            app.speak_button.config(state=tk.DISABLED)
        if hasattr(app, 'save_button'):
            app.save_button.config(state=tk.DISABLED)
        # قد نرغب في تعطيل أزرار النسخ واللصق أيضاً إذا لم يكن هناك فائدة منها
        # ولكن عادة ما تظل مفيدة لإدارة النص
    else:
        if not app.voice_dropdown.get() and app.system_voices:
            app.voice_dropdown.current(0)
            app.on_voice_change()

    root.mainloop()