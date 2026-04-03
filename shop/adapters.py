from allauth.socialaccount.adapter import DefaultSocialAccountAdapter  # type: ignore

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Jika user belum ada, biarkan Allauth mencoba menyambungkan 
        # email secara otomatis jika ada email yang sama
        pass

    def save_user(self, request, sociallogin, form=None):
        # Paksa penyimpanan user tanpa melalui form pendaftaran tambahan
        user = super().save_user(request, sociallogin, form)
        return user