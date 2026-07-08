"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { User, Building2, Shield, Bell, Palette, Save, Loader2, CheckCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/lib/api";
import toast from "react-hot-toast";

const profileSchema = z.object({
  full_name: z.string().min(2, "Name too short"),
  username: z.string().min(3, "Username too short"),
  email: z.string().email("Invalid email"),
});
type ProfileForm = z.infer<typeof profileSchema>;

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "security", label: "Security", icon: Shield },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
] as const;

type TabId = typeof TABS[number]["id"];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [saving, setSaving] = useState(false);
  const { user, loadUser } = useAuthStore();

  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || "",
      username: user?.username || "",
      email: user?.email || "",
    },
  });

  useEffect(() => {
    if (user) {
      reset({
        full_name: user.full_name || "",
        username: user.username || "",
        email: user.email || "",
      });
    }
  }, [user, reset]);

  const onSaveProfile = async (data: ProfileForm) => {
    setSaving(true);
    try {
      await authApi.updateProfile(data);
      await loadUser();
      toast.success("Profile updated!");
      reset(data);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Update failed";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const InputField = ({ label, name, type = "text", register: reg, error, disabled = false }: {
    label: string;
    name: string;
    type?: string;
    register: ReturnType<typeof useForm<ProfileForm>["register"]>;
    error?: string;
    disabled?: boolean;
  }) => (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-slate-300">{label}</label>
      <input
        type={type}
        {...reg}
        disabled={disabled}
        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 text-sm mt-0.5">Manage your account and platform preferences</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <div className="w-52 flex-shrink-0 space-y-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeTab === id
                  ? "bg-indigo-600/20 text-indigo-400 border border-indigo-600/30"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === "profile" && (
            <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-6">
              <div>
                <h2 className="font-semibold text-white text-lg">Profile Information</h2>
                <p className="text-slate-500 text-sm mt-0.5">Update your personal details</p>
              </div>

              {/* Avatar */}
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-2xl font-bold">
                  {user?.full_name?.[0]?.toUpperCase() || "U"}
                </div>
                <div>
                  <div className="text-sm font-medium text-white">{user?.full_name}</div>
                  <div className="text-xs text-slate-500 mt-0.5 capitalize">{user?.role?.replace("_", " ")}</div>
                  <button className="text-xs text-indigo-400 hover:text-indigo-300 mt-1 transition-colors">Change avatar</button>
                </div>
              </div>

              <form onSubmit={handleSubmit(onSaveProfile)} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <InputField
                    label="Full Name"
                    name="full_name"
                    register={register("full_name")}
                    error={errors.full_name?.message}
                  />
                  <InputField
                    label="Username"
                    name="username"
                    register={register("username")}
                    error={errors.username?.message}
                  />
                </div>
                <InputField
                  label="Email"
                  name="email"
                  type="email"
                  register={register("email")}
                  error={errors.email?.message}
                />
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={saving || !isDirty}
                    className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-60"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {activeTab === "organization" && (
            <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="font-semibold text-white text-lg">Organization</h2>
                <p className="text-slate-500 text-sm mt-0.5">Manage your organization settings</p>
              </div>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-slate-300">Organization Name</label>
                  <input
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    placeholder="Acme Corp"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-slate-300">Industry</label>
                  <select className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 appearance-none">
                    <option>Technology</option>
                    <option>Healthcare</option>
                    <option>Finance</option>
                    <option>Education</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4">
                <div className="text-sm font-medium text-indigo-400 mb-1">Current Plan: Free</div>
                <div className="text-xs text-slate-400">
                  Upgrade to Pro for unlimited resumes, advanced AI features, and priority support.
                </div>
                <button className="mt-3 text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition-all">
                  Upgrade to Pro
                </button>
              </div>
            </motion.div>
          )}

          {activeTab === "security" && (
            <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="font-semibold text-white text-lg">Security</h2>
                <p className="text-slate-500 text-sm mt-0.5">Manage password and account security</p>
              </div>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-slate-300">Current Password</label>
                  <input type="password" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-slate-300">New Password</label>
                  <input type="password" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-slate-300">Confirm New Password</label>
                  <input type="password" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
                </div>
                <div className="flex justify-end">
                  <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <Shield className="w-4 h-4" />
                    Update Password
                  </button>
                </div>
              </div>

              <div className="border-t border-slate-700/50 pt-5 space-y-3">
                <h3 className="font-medium text-white text-sm">Active Sessions</h3>
                <div className="bg-slate-800/60 rounded-xl p-4 flex items-center justify-between">
                  <div>
                    <div className="text-sm text-white">Current session</div>
                    <div className="text-xs text-slate-500 mt-0.5">Chrome on macOS · Active now</div>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <CheckCircle className="w-3.5 h-3.5" /> Current
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === "notifications" && (
            <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="font-semibold text-white text-lg">Notifications</h2>
                <p className="text-slate-500 text-sm mt-0.5">Control how you receive updates</p>
              </div>
              <div className="space-y-4">
                {[
                  { label: "New candidate uploads", desc: "Get notified when new resumes are uploaded", defaultOn: true },
                  { label: "Ranking completed", desc: "Alert when AI ranking finishes", defaultOn: true },
                  { label: "Pipeline stage changes", desc: "Notify when candidates move between stages", defaultOn: false },
                  { label: "Training completed", desc: "Alert when model training finishes", defaultOn: true },
                  { label: "Weekly analytics report", desc: "Receive a weekly summary of hiring activity", defaultOn: false },
                ].map(({ label, desc, defaultOn }) => (
                  <div key={label} className="flex items-start justify-between gap-4 p-4 bg-slate-800/40 rounded-xl">
                    <div>
                      <div className="text-sm font-medium text-white">{label}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                    </div>
                    <button
                      className={`relative w-10 h-6 rounded-full transition-all flex-shrink-0 ${defaultOn ? "bg-indigo-600" : "bg-slate-700"}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${defaultOn ? "left-5" : "left-1"}`} />
                    </button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {activeTab === "appearance" && (
            <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
              className="bg-slate-900/80 border border-slate-700/50 rounded-2xl p-6 space-y-5">
              <div>
                <h2 className="font-semibold text-white text-lg">Appearance</h2>
                <p className="text-slate-500 text-sm mt-0.5">Customize your interface</p>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-medium text-slate-300 mb-3">Theme</div>
                  <div className="grid grid-cols-3 gap-3">
                    {["Dark", "Light", "System"].map((t) => (
                      <button
                        key={t}
                        className={`p-3 rounded-xl border text-sm font-medium transition-all ${
                          t === "Dark"
                            ? "border-indigo-500/60 bg-indigo-500/10 text-indigo-400"
                            : "border-slate-700 text-slate-400 hover:border-slate-600 hover:text-white"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-300 mb-3">Accent Color</div>
                  <div className="flex gap-2">
                    {[
                      { name: "Indigo", color: "bg-indigo-500" },
                      { name: "Violet", color: "bg-violet-500" },
                      { name: "Emerald", color: "bg-emerald-500" },
                      { name: "Rose", color: "bg-rose-500" },
                      { name: "Amber", color: "bg-amber-500" },
                    ].map(({ name, color }) => (
                      <button
                        key={name}
                        title={name}
                        className={`w-8 h-8 rounded-full ${color} border-2 ${name === "Indigo" ? "border-white" : "border-transparent"} transition-all hover:scale-110`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
