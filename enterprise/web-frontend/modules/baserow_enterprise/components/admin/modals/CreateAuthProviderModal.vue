<template>
  <Modal>
    <h2 class="box__title">
      {{
        $t('createSettingsAuthProviderModal.title', {
          type: getProviderTypeName(),
        })
      }}
    </h2>
    <div v-if="authProviderType">
      <component
        :is="getProviderAdminSettingsFormComponent()"
        ref="providerSettingsForm"
        :auth-provider-type="authProviderType"
        @submit="create($event)"
      >
        <div class="actions">
          <ul class="action__links">
            <li>
              <a @click="$emit('cancel')">{{ $t('action.cancel') }}</a>
            </li>
          </ul>
          <Button type="primary" :disabled="loading" :loading="loading">
            {{ $t('action.create') }}</Button
          >
        </div>
      </component>
    </div>
  </Modal>
</template>

<script>
import modal from '@baserow/modules/core/mixins/modal'
import { notifyIf } from '@baserow/modules/core/utils/error'

export default {
  name: 'CreateAuthProviderModal',
  mixins: [modal],
  props: {
    authProviderType: {
      type: String,
      required: false,
      default: null,
    },
  },
  data() {
    return {
      loading: false,
    }
  },
  methods: {
    getProviderAdminSettingsFormComponent() {
      return this.$registry
        .get('authProvider', this.authProviderType)
        .getAdminSettingsFormComponent()
    },
    getProviderTypeName() {
      if (!this.authProviderType) return ''

      return this.$registry.get('authProvider', this.authProviderType).getName()
    },
    async create(values) {
      this.loading = true
      this.serverErrors = {}
      try {
        await this.$store.dispatch('authProviderAdmin/create', {
          type: this.authProviderType,
          values,
        })
        this.$emit('created')
      } catch (error) {
        if (!this.$refs.providerSettingsForm.handleServerError(error)) {
          notifyIf(error, 'settings')
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
