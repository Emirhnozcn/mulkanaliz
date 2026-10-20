<script setup lang="ts">
definePageMeta({ layout: 'auth' })
const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase).replace(/\/$/, '')
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const fullName = ref('')
const registrationCode = ref('')
const error = ref('')
const notice = ref('')
const loading = ref(false)
async function submit() {
  error.value = ''; notice.value = ''; loading.value = true
  try {
    if (mode.value === 'register') {
      await $fetch(`${apiBase}/auth/register`, { method: 'POST', body: { username: username.value, password: password.value, full_name: fullName.value, registration_code: registrationCode.value } })
      notice.value = 'Kayıt oluşturuldu. Şimdi giriş yapabilirsiniz.'
      mode.value = 'login'
    } else {
      const result = await $fetch<{ access_token: string; user: { full_name: string; role: string } }>(`${apiBase}/auth/login`, { method: 'POST', body: { username: username.value, password: password.value } })
      if (import.meta.client) {
        sessionStorage.setItem('rea_access_token', result.access_token)
        sessionStorage.setItem('rea_user', JSON.stringify(result.user))
      }
      await navigateTo('/')
    }
  } catch (e: any) { error.value = e?.data?.detail || e?.message || 'İşlem başarısız oldu.' }
  finally { loading.value = false }
}
</script>
<template>
  <div class="login-page"><section class="login-card">
    <NuxtLink to="/" class="brand"><span class="brand-mark">M</span><span><b>MülkAnaliz</b><small>GAYRİMENKUL İSTİHBARATI</small></span></NuxtLink>
    <p class="eyebrow">EMLAK OFİSİ ÇALIŞMA ALANI</p><h1>{{ mode === 'login' ? 'Tekrar hoş geldiniz' : 'Çalışan kaydı' }}</h1>
    <p>{{ mode === 'login' ? 'Ofis hesabınızla giriş yapın.' : 'Kayıt olmak için ofis yöneticinizden aldığınız kayıt kodu gereklidir.' }}</p>
    <form @submit.prevent="submit">
      <div v-if="mode === 'register'" class="field"><label>Ad soyad</label><input v-model.trim="fullName" required minlength="2" autocomplete="name" /></div>
      <div v-if="mode === 'register'" class="field"><label>Kullanıcı adı</label><input v-model.trim="username" required minlength="3" maxlength="40" pattern="[A-Za-z0-9_.-]+" autocomplete="username" /></div>
      <div v-else class="field"><label>Kullanıcı adı</label><input v-model.trim="username" required minlength="3" maxlength="40" autocomplete="username" /></div>
      <div class="field"><label>Parola (en az 12 karakter)</label><input v-model="password" required minlength="12" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" /></div>
      <div v-if="mode === 'register'" class="field"><label>Ofis kayıt kodu</label><input v-model="registrationCode" required type="password" autocomplete="off" /></div>
      <div v-if="error" class="alert alert-warning" role="alert">{{ error }}</div><div v-if="notice" class="alert" role="status">{{ notice }}</div>
      <button class="button button-primary" type="submit" :disabled="loading" style="width:100%;margin-top:18px">{{ loading ? 'Bekleyin…' : mode === 'login' ? 'Giriş yap' : 'Çalışan kaydı oluştur' }}</button>
    </form>
    <p class="panel-footnote">{{ mode === 'login' ? 'Ofis çalışanı mısınız?' : 'Zaten hesabınız var mı?' }} <button type="button" class="link-button" @click="mode = mode === 'login' ? 'register' : 'login'; error = ''; notice = ''">{{ mode === 'login' ? 'Kayıt ol' : 'Giriş yap' }}</button></p>
    
    <p class="panel-footnote">Kayıt kodu yalnızca ofis çalışanlarıyla paylaşılmalıdır. Güçlü ve benzersiz bir parola kullanın.</p>
  </section></div>
</template>
<style scoped>.link-button{border:0;background:transparent;color:var(--primary,#2457d6);cursor:pointer;font:inherit;text-decoration:underline;padding:0}.field{margin-top:14px}.field input{width:100%}form{margin-top:20px}</style>
