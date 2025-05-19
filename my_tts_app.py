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
        self.root.geometry("600x450")

        self.engine = pyttsx3.init()
        
        # --- واجهة المستخدم ---
        input_frame = ttk.LabelFrame(root, text="النص المراد تحويله")
        input_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10, font=("Arial", 12))
        self.text_area.pack(padx=5, pady=5, fill="both", expand=True)
        self.text_area.insert(tk.END, "مرحباً بك في تطبيق تحويل النص إلى كلام.")

        # =====================================================================
        # انقل تعريف status_label إلى هنا أو قبلها
        self.status_label = ttk.Label(root, text="الحالة: جاهز")
        # لا تقم بعمل .pack() هنا بعد، سنقوم بذلك في نهاية الـ __init__
        # أو يمكنك عمل .pack() هنا إذا كنت تريد ظهوره في مكان معين مبكراً
        # ولكن من الأفضل تجميع كل الـ .pack() أو .grid() في ترتيب منطقي.
        # دعنا نؤجل .pack() إلى مكانه الأصلي في الأسفل.
        # =====================================================================

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
            self.set_selected_voice() # <--- الآن status_label موجود عند استدعاء هذه الدالة
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
        self.update_volume_label()
        self.volume_percent_label = ttk.Label(settings_frame, textvariable=self.volume_percent_label_var)
        self.volume_percent_label.grid(row=2, column=2, padx=5, pady=5)

        settings_frame.columnconfigure(1, weight=1)

        control_frame = ttk.Frame(root)
        control_frame.pack(padx=10, pady=(5, 10), fill="x")

        self.speak_button = ttk.Button(control_frame, text="🔊 تحدث", command=self.speak_text_threaded)
        self.speak_button.pack(side=tk.LEFT, padx=(0, 5))

        self.save_button = ttk.Button(control_frame, text="💾 حفظ كـ WAV", command=self.save_audio_threaded)
        self.save_button.pack(side=tk.LEFT)
        
        # الآن قم بعمل pack لـ status_label بعد تعريف كل العناصر التي فوقه
        self.status_label.pack(pady=(0, 5))


    def update_volume_label(self, event=None):
        self.volume_percent_label_var.set(f"{int(self.voice_volume.get() * 100)}%")


    def find_system_voices(self):
        voices_props = []
        voices = self.engine.getProperty('voices')
        for voice in voices:
            voices_props.append({'id': voice.id, 'name': voice.name, 'lang': voice.languages})
        # لا نعرض messagebox هنا مباشرة لأن الواجهة الرئيسية قد لا تكون جاهزة بالكامل
        # يمكن معالجة حالة عدم وجود أصوات بشكل مختلف إذا لزم الأمر
        # if not voices_props:
        #     messagebox.showwarning("لا توجد أصوات", "لم يتم العثور على أي أصوات مثبتة على النظام.")
        return voices_props

    def set_selected_voice(self):
        # التأكد أن status_label موجود قبل استخدامه
        if not hasattr(self, 'status_label'):
             # هذا لا ينبغي أن يحدث إذا تم التعريف بشكل صحيح في __init__
            print("تحذير: status_label غير مهيأ عند استدعاء set_selected_voice")
            return

        selected_voice_name = self.selected_voice_id.get()
        if not selected_voice_name:
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
                # هنا تظهر رسالة الخطأ الأصلية التي رأيتها
                messagebox.showerror("خطأ", f"فشل في تحديد الصوت: {e}")
                self.status_label.config(text="الحالة: خطأ في تحديد الصوت.")
        else:
            self.status_label.config(text=f"الحالة: لم يتم العثور على تعريف الصوت لـ {selected_voice_name}")

    def on_voice_change(self, event=None):
        self.set_selected_voice()

    def on_settings_change(self, event=None):
        try:
            self.engine.setProperty('rate', self.voice_rate.get())
            self.engine.setProperty('volume', self.voice_volume.get())
            self.update_volume_label() 
            self.status_label.config(text="الحالة: تم تحديث الإعدادات.")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تحديث الإعدادات: {e}")
            self.status_label.config(text="الحالة: خطأ في تحديث الإعدادات.")

    def _process_audio(self, text, save_path=None):
        if not text.strip():
            messagebox.showwarning("تنبيه", "الرجاء إدخال نص ليتم تحويله.")
            return False

        self.status_label.config(text="الحالة: جاري معالجة الصوت...")
        self.speak_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.root.update_idletasks()

        try:
            self.engine.setProperty('rate', self.voice_rate.get())
            self.engine.setProperty('volume', self.voice_volume.get())
            self.set_selected_voice() # التأكد من أن الصوت المختار هو المحدد


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
            self.root.update_idletasks()

    def speak_text_threaded(self):
        text_to_speak = self.text_area.get("1.0", tk.END).strip()
        threading.Thread(target=self._process_audio, args=(text_to_speak,), daemon=True).start()

    def save_audio_threaded(self):
        text_to_speak = self.text_area.get("1.0", tk.END).strip()
        if not text_to_speak:
            messagebox.showwarning("تنبيه", "الرجاء إدخال نص ليتم تحويله وحفظه.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".wav", 
            filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3"), ("All files", "*.*")],
            title="حفظ الملف الصوتي"
        )
        if not save_path:
            return

        threading.Thread(target=self._process_audio, args=(text_to_speak, save_path), daemon=True).start()


if __name__ == "__main__":
    try:
        import pyttsx3
    except ImportError:
        print("مكتبة pyttsx3 غير مثبتة. جاري محاولة التثبيت...")
        if os.system("pip install pyttsx3 pypiwin32") == 0: 
            print("تم تثبيت pyttsx3. يرجى إعادة تشغيل التطبيق.")
        else:
            print("فشل تثبيت pyttsx3. يرجى تثبيتها يدوياً: pip install pyttsx3 pypiwin32")
        exit()

    root = tk.Tk()
    app = SystemTTSApp(root)
    # التحقق من وجود أصوات بعد تهيئة الواجهة بالكامل
    if not app.system_voices:
        messagebox.showwarning("لا توجد أصوات", "لم يتم العثور على أي أصوات مثبتة على النظام. قد لا يعمل التطبيق بشكل صحيح.")
        # يمكنك هنا تعطيل بعض الأزرار أو اتخاذ إجراء آخر
        if hasattr(app, 'voice_dropdown'): # التحقق من وجود voice_dropdown قبل محاولة تعطيله
            app.voice_dropdown.config(state=tk.DISABLED)
        if hasattr(app, 'speak_button'):
            app.speak_button.config(state=tk.DISABLED)
        if hasattr(app, 'save_button'):
            app.save_button.config(state=tk.DISABLED)

    root.mainloop()