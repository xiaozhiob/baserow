<template>
  <div>
    <SidebarApplication
      ref="sidebarApplication"
      :workspace="workspace"
      :application="application"
      @selected="selected"
    >
      <template #context>
        <li
          v-if="
            $hasPermission(
              'application.update',
              application,
              application.workspace.id
            )
          "
          class="context__menu-item"
        >
          <a class="context__menu-item-link" @click="settingsClicked">
            <i class="context__menu-item-icon iconoir-settings"></i>
            {{ $t('sidebarComponentBuilder.settings') }}
          </a>
        </li>
      </template>
      <template v-if="isAppSelected(application)" #body>
        <ul class="tree__subs">
          <SidebarItemBuilder
            v-for="page in orderedPages"
            :key="page.id"
            v-sortable="{
              id: page.id,
              update: orderPages,
              marginLeft: 34,
              marginRight: 10,
              marginTop: -1.5,
              enabled: $hasPermission(
                'builder.order_pages',
                application,
                application.workspace.id
              ),
            }"
            :builder="application"
            :page="page"
          ></SidebarItemBuilder>
        </ul>
        <ul v-if="pendingJobs.length" class="tree__subs">
          <component
            :is="getPendingJobComponent(job)"
            v-for="job in pendingJobs"
            :key="job.id"
            :job="job"
          >
          </component>
        </ul>
        <a
          v-if="
            $hasPermission(
              'builder.create_page',
              application,
              application.workspace.id
            )
          "
          class="tree__sub-add"
          @click="$refs.createPageModal.show()"
        >
          <i class="iconoir-plus"></i>
          {{ $t('sidebarComponentBuilder.createPage') }}
        </a>
        <CreatePageModal
          ref="createPageModal"
          :builder="application"
          :workspace="application.workspace"
        ></CreatePageModal>
      </template>
    </SidebarApplication>
    <BuilderSettingsModal ref="builderSettingsModal" :builder="application" />
  </div>
</template>

<script>
import SidebarApplication from '@baserow/modules/core/components/sidebar/SidebarApplication'
import BuilderSettingsModal from '@baserow/modules/builder/components/settings/BuilderSettingsModal'
import { mapGetters } from 'vuex'
import { notifyIf } from '@baserow/modules/core/utils/error'
import SidebarItemBuilder from '@baserow/modules/builder/components/sidebar/SidebarItemBuilder'
import CreatePageModal from '@baserow/modules/builder/components/page/CreatePageModal'

export default {
  name: 'TemplateSidebar',
  components: {
    CreatePageModal,
    SidebarItemBuilder,
    BuilderSettingsModal,
    SidebarApplication,
  },
  props: {
    application: {
      type: Object,
      required: true,
    },
    workspace: {
      type: Object,
      required: true,
    },
  },
  computed: {
    ...mapGetters({
      isAppSelected: 'application/isSelected',
      allJobs: 'job/getAll',
    }),
    orderedPages() {
      return this.application.pages
        .map((page) => page)
        .sort((a, b) => a.order - b.order)
    },
    pendingJobs() {
      return this.allJobs.filter((job) =>
        this.$registry
          .get('job', job.type)
          .isJobPartOfApplication(job, this.application)
      )
    },
  },
  methods: {
    selected(application) {
      try {
        this.$store.dispatch('application/select', application)
      } catch (error) {
        notifyIf(error, 'workspace')
      }
    },
    settingsClicked() {
      this.$refs.sidebarApplication.$refs.context.hide()
      this.$refs.builderSettingsModal.show()
    },
    orderPages(order, oldOrder) {
      try {
        this.$store.dispatch('page/order', {
          builder: this.application,
          order,
          oldOrder,
        })
      } catch (error) {
        notifyIf(error, 'page')
      }
    },
    getPendingJobComponent(job) {
      return this.$registry.get('job', job.type).getSidebarComponent()
    },
  },
}
</script>
