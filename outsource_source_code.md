# Push To Kindle Progress Page - Technical Specification

## Goal

Add a new page to the Komga web interface that displays log output from the push_to_kindle.py script. This page should be accessible from the sidebar navigation as a subcategory of History. The existing History page should be renamed to "Scan History" and both should be organized under a History menu in the sidebar.

## Complete Folder Structure

```
komga/
├── komga-webui/
│   ├── src/
│   │   ├── views/
│   │   │   ├── HistoryView.vue (existing - needs to be renamed/modified)
│   │   │   ├── PushToKindleProgressView.vue (new - needs to be created)
│   │   │   └── HomeView.vue (existing - needs sidebar modification)
│   │   ├── router.ts (existing - needs route modification)
│   │   ├── locales/ (existing - may need translation updates)
│   │   ├── services/ (existing - may need new service for logs)
│   │   └── types/ (existing - may need new type definitions)
│   └── public/
└── komga/
    └── src/
        └── main/
            └── kotlin/
                └── org/
                    └── gotson/
                        └── komga/
                            └── interfaces/
                                └── api/
                                    └── rest/
                                        ├── BookController.kt (existing - needs modification for log capture)
                                        ├── SeriesController.kt (existing - needs modification for log capture)
                                        └── KindleLogController.kt (new - needs to be created)
```

## Source Code

### Frontend Files

#### File: komga-webui/src/views/HistoryView.vue
- **Current Purpose**: Displays historical events (book deletions, imports, etc.)
- **Required Changes**: 
  - Rename to "ScanHistoryView.vue"
  - Update component name to "ScanHistoryView"
  - Update all references to match new name
  - Modify page title and headers to display "Scan History"


```python
<template>
  <v-container fluid class="pa-6">
    <v-data-table
      :headers="headers"
      :items="items"
      :options.sync="options"
      :server-items-length="totalElements"
      :loading="loading"
      sort-by="timestamp"
      :sort-desc="true"
      multi-sort
      class="elevation-1"
      :footer-props="{
        itemsPerPageOptions: [20, 50, 100]
      }"
    >
      <template v-slot:item.type="{ item }">
        <v-icon :title="$t(`enums.historical_event_type.${item.type}`)">{{ getIcon(item.type) }}</v-icon>
      </template>

      <template v-slot:item.seriesId="{ item }">
        <router-link v-if="getSeries(item.seriesId)"
                     :to="{name: 'browse-series', params: {seriesId: item.seriesId}}"
                     class="link-underline"
        >{{ getSeries(item.seriesId).metadata.title }}
        </router-link>
        <template v-else>{{ item.seriesId }}</template>
      </template>

      <template v-slot:item.bookId="{ item }">
        <router-link v-if="getBook(item.bookId)"
                     :to="{name: 'browse-book', params: {bookId: item.bookId}}"
                     class="link-underline"
        >{{ getBook(item.bookId).metadata.title }}
        </router-link>
        <template v-else>{{ item.bookId }}</template>
      </template>

      <template v-slot:item.timestamp="{ item }">
        {{
          new Intl.DateTimeFormat($i18n.locale, {
            dateStyle: 'medium',
            timeStyle: 'short'
          }).format(item.timestamp)
        }}
      </template>

      <template v-slot:item.properties="{ item }">
        <v-btn icon small @click="showDetails(item)">
          <v-icon small>mdi-information</v-icon>
        </v-btn>
      </template>

      <template v-slot:footer.prepend>
        <v-btn icon @click="loadData">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </template>

    </v-data-table>

    <v-dialog
      v-model="dialogDetails"
      scrollable
    >
      <v-card v-if="dialogDetailsItem">
        <v-card-title>{{ $t(`enums.historical_event_type.${dialogDetailsItem.type}`) }}</v-card-title>
        <v-card-text>
          <v-simple-table>
            <tbody>
            <tr v-for="[key, value] in Object.entries(dialogDetailsItem.properties)" :key="key">
              <td class="text-capitalize font-weight-bold">{{ key }}</td>
              <td>{{ value }}</td>
            </tr>
            <tr v-if="getPageHash(dialogDetailsItem)">
              <td class="font-weight-bold">Page</td>
              <td>
                <v-img
                  width="200"
                  height="300"
                  contain
                  :src="pageHashKnownThumbnailUrl(getPageHash(dialogDetailsItem))"
                />
              </td>
            </tr>
            </tbody>
          </v-simple-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer/>
          <v-btn @click="dialogDetails = false" text>{{ $t('common.close') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts">
import Vue from 'vue'
import {HistoricalEventDto} from '@/types/komga-history'
import {SeriesDto} from '@/types/komga-series'
import {BookDto} from '@/types/komga-books'
import {pageHashKnownThumbnailUrl} from '@/functions/urls'
import {PageHashKnownDto} from '@/types/komga-pagehashes'

export default Vue.extend({
  name: 'HistoryView',
  data: function () {
    return {
      pageHashKnownThumbnailUrl,
      items: [] as HistoricalEventDto[],
      totalElements: 0,
      loading: true,
      options: {} as any,
      dialogDetails: false,
      dialogDetailsItem: undefined as HistoricalEventDto | undefined,
      seriesCache: [] as SeriesDto[],
      seriesCacheNotFound: [] as string[],
      booksCache: [] as BookDto[],
      booksCacheNotFound: [] as string[],
    }
  },
  watch: {
    options: {
      handler() {
        this.loadData()
      },
      deep: true,
    },
  },
  computed: {
    headers(): object[] {
      return [
        {text: this.$t('history.header.type').toString(), value: 'type'},
        {text: this.$t('history.header.series').toString(), value: 'seriesId'},
        {text: this.$t('history.header.book').toString(), value: 'bookId'},
        {text: this.$t('history.header.date').toString(), value: 'timestamp'},
        {text: this.$t('history.header.details').toString(), value: 'properties', sortable: false},
      ]
    },
  },
  methods: {
    getPageHash(item: HistoricalEventDto): PageHashKnownDto | undefined {
      if (item.type !== 'DuplicatePageDeleted') return undefined
      let size: any = item.properties['page file size' as any]
      if (size === 'null') size = -1
      return {
        hash: item.properties['page file hash' as any],
        size: size,
        mediaType: item.properties['page media type' as any],
      } as any
    },
    getSeries(seriesId: string): SeriesDto | undefined {
      return this.seriesCache.find(x => x.id === seriesId)
    },
    getBook(bookId: string): BookDto | undefined {
      return this.booksCache.find(x => x.id === bookId)
    },
    showDetails(item: HistoricalEventDto) {
      this.dialogDetailsItem = item
      this.dialogDetails = true
    },
    getIcon(type: string): string {
      switch (type) {
        case 'BookFileDeleted':
          return 'mdi-file-remove'
        case 'SeriesFolderDeleted':
          return 'mdi-folder-remove'
        case 'DuplicatePageDeleted':
          return 'mdi-book-minus'
        case 'BookConverted':
          return 'mdi-archive-refresh'
        case 'BookImported':
          return 'mdi-import'
        default:
          return ''
      }
    },
    async loadData() {
      this.loading = true

      const {sortBy, sortDesc, page, itemsPerPage} = this.options

      const pageRequest = {
        page: page - 1,
        size: itemsPerPage,
        sort: [],
      } as PageRequest

      for (let i = 0; i < sortBy.length; i++) {
        pageRequest.sort!!.push(`${sortBy[i]},${sortDesc[i] ? 'desc' : 'asc'}`)
      }

      const itemsPage = await this.$komgaHistory.getAll(pageRequest)
      this.totalElements = itemsPage.totalElements
      this.items = itemsPage.content

      for (const seriesId of new Set(this.items.map(x => x.seriesId))) {
        if (seriesId && !this.seriesCacheNotFound.includes(seriesId) && !this.getSeries(seriesId)) {
          this.$komgaSeries.getOneSeries(seriesId)
            .then(s => this.seriesCache.push(s))
            .catch(() => this.seriesCacheNotFound.push(seriesId))
        }
      }

      for (const bookId of new Set(this.items.map(x => x.bookId))) {
        if (bookId && !this.booksCacheNotFound.includes(bookId) && !this.getBook(bookId)) {
          this.$komgaBooks.getBook(bookId)
            .then(b => this.booksCache.push(b))
            .catch(() => this.booksCacheNotFound.push(bookId))
        }
      }

      this.loading = false
    },
  },
})
</script>

<style scoped>

</style>

```
#### File: komga-webui/src/views/PushToKindleProgressView.vue (NEW)
- **Purpose**: Display log output from push_to_kindle.py script
- **Requirements**:
  - Display logs in a scrollable text area with monospace font
  - Auto-refresh logs every 5 seconds
  - Show timestamp for each log entry
  - Include manual refresh button
  - Show clear logs button
  - Display loading indicator while fetching logs
  - Handle error states gracefully
  - Use Vuetify components for consistent UI

#### File: komga-webui/src/views/HomeView.vue
- **Current Purpose**: Main layout with sidebar navigation
- **Required Changes**:
  - Modify sidebar navigation structure to create History menu group
  - Add "Scan History" as first submenu item
  - Add "Push To Kindle Progress" as second submenu item
  - Update icons and routing accordingly
  - Update navigation logic to handle expanded/collapsed state


```python
<template>
  <div class="fill-height">
    <v-app-bar
      app
    >
      <v-badge
        dot
        offset-x="15"
        offset-y="20"
        :value="drawerVisible ? 0 : $store.state.booksToCheck + $store.getters.getUnreadAnnouncementsCount()"
        :color="$store.state.booksToCheck ? 'accent' : 'info'"
        class="ms-n3"
      >
        <v-app-bar-nav-icon @click.stop="toggleDrawer"/>
      </v-badge>

      <search-box class="flex-fill"/>

    </v-app-bar>

    <v-navigation-drawer app v-model="drawerVisible" :right="$vuetify.rtl">
      <v-list-item @click="$router.push({name: 'home'})" inactive class="pb-2">
        <v-list-item-avatar>
          <v-img src="../assets/logo.svg"/>
        </v-list-item-avatar>

        <v-list-item-content>
          <v-list-item-title class="title">
            Komga
          </v-list-item-title>
        </v-list-item-content>

        <v-tooltip left>
          <template v-slot:activator="{ on }">
            <v-progress-linear
              :active="taskCount > 0"
              indeterminate
              absolute
              bottom
              height="5"
              color="secondary"
              v-on="on"
            />
          </template>
          <div class="mb-2">{{ $tc('common.pending_tasks', taskCount) }}</div>
          <div v-for="taskType in Object.keys(taskCountByType)"
               :key="taskType"
          >{{ taskType }}: {{ taskCountByType[taskType] }}
          </div>
        </v-tooltip>
      </v-list-item>

      <v-divider/>

      <v-slide-x-transition hide-on-leave>
        <reorder-libraries v-if="showReorder" @dismiss="showReorder = false"/>
      </v-slide-x-transition>

      <template v-if="!showReorder">
        <v-list nav shaped dense>
          <v-list-item :to="{name: 'dashboard'}">
            <v-list-item-icon>
              <v-icon>mdi-home</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>{{ $t('navigation.home') }}</v-list-item-title>
            </v-list-item-content>
          </v-list-item>

          <!--   LIBRARIES     -->
          <v-list-item :to="{name:'libraries', params: {libraryId: LIBRARIES_ALL}}">
            <v-list-item-icon>
              <v-icon>mdi-book-multiple</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>{{ $t('navigation.libraries') }}</v-list-item-title>
            </v-list-item-content>
            <v-list-item-action v-if="isAdmin" class="ma-0">
              <v-btn icon @click.stop.capture.prevent="addLibrary">
                <v-icon>mdi-plus</v-icon>
              </v-btn>
            </v-list-item-action>
            <v-list-item-action class="ma-0">
              <libraries-actions-menu @reorder="showReorder = true"/>
            </v-list-item-action>
          </v-list-item>

          <!--   PINNED LIBRARIES     -->
          <v-list-item v-for="(l, index) in librariesPinned"
                       :key="index"
                       :to="{name:'libraries', params: {libraryId: l.id}}"
          >
            <v-list-item-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>{{ l.name }}</v-list-item-title>
              <v-list-item-subtitle
                v-if="l.unavailable"
                class="error--text caption"
              >{{ $t('common.unavailable') }}
              </v-list-item-subtitle>
            </v-list-item-content>
            <v-list-item-action class="ma-0" v-if="isAdmin">
              <library-actions-menu :library="l"/>
            </v-list-item-action>
          </v-list-item>

          <!--   UNPINNED LIBRARIES     -->
          <v-list-group no-action
                        sub-group
                        v-if="librariesUnpinned.length > 0"
                        v-model="expandUnpinned"
          >
            <template v-slot:activator>
              <v-list-item-title>{{ $t('common.more') }}</v-list-item-title>
            </template>

            <v-list-item v-for="(l, index) in librariesUnpinned"
                         :key="index"
                         :to="{name:'libraries', params: {libraryId: l.id}}"
            >
              <v-list-item-content>
                <v-list-item-title>{{ l.name }}</v-list-item-title>
                <v-list-item-subtitle
                  v-if="l.unavailable"
                  class="error--text caption"
                >{{ $t('common.unavailable') }}
                </v-list-item-subtitle>
              </v-list-item-content>
              <v-list-item-action class="ma-0">
                <library-actions-menu :library="l"/>
              </v-list-item-action>
            </v-list-item>
          </v-list-group>

          <!--   IMPORT     -->
          <v-list-group v-if="isAdmin"
                        prepend-icon="mdi-import"
                        no-action
                        v-model="expandImport"
          >
            <template v-slot:activator>
              <v-list-item-title>{{ $t('book_import.title') }}</v-list-item-title>
            </template>

            <v-list-item :to="{name: 'import-books'}">
              <v-list-item-title>{{ $t('common.books') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'import-readlist'}">
              <v-list-item-title>{{ $t('common.readlist') }}</v-list-item-title>
            </v-list-item>
          </v-list-group>

          <!--   MEDIA MANAGEMENT     -->
          <v-list-group v-if="isAdmin"
                        no-action
                        v-model="expandMediaManagement"
          >
            <template v-slot:prependIcon>
              <v-badge
                dot
                inline
                :value="$store.state.booksToCheck"
                color="accent"
              >
                <v-icon>mdi-book-cog</v-icon>
              </v-badge>
            </template>
            <template v-slot:activator>
              <v-list-item-title>{{ $t('common.media') }}</v-list-item-title>
            </template>

            <v-list-item :to="{name: 'media-analysis'}">
              <v-badge
                dot
                inline
                :value="$store.state.booksToCheck"
                color="accent"
              >
                <v-list-item-title>{{ $t('media_analysis.media_analysis') }}</v-list-item-title>
              </v-badge>
            </v-list-item>

            <v-list-item :to="{name: 'missing-posters'}">
              <v-list-item-title>{{ $t('missing_posters.title') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'duplicate-files'}">
              <v-list-item-title>{{ $t('duplicates.title') }}</v-list-item-title>
            </v-list-item>

            <v-list-group no-action
                          sub-group
                          v-model="expandDuplicatePages"
            >
              <template v-slot:activator>
                <v-list-item-title>{{ $t('duplicate_pages.title') }}</v-list-item-title>
              </template>

              <v-list-item :to="{name: 'settings-duplicate-pages-known'}">
                <v-list-item-title>{{ $t('duplicate_pages.known') }}</v-list-item-title>
              </v-list-item>

              <v-list-item :to="{name: 'settings-duplicate-pages-unknown'}">
                <v-list-item-title>{{ $t('duplicate_pages.new') }}</v-list-item-title>
              </v-list-item>
            </v-list-group>
          </v-list-group>

          <v-list-item :to="{name: 'history'}" v-if="isAdmin">
            <v-list-item-icon>
              <v-icon>mdi-clock-time-four-outline</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>{{ $t('history.title') }}</v-list-item-title>
            </v-list-item-content>
          </v-list-item>

          <!--   SETTINGS     -->
          <v-list-group v-if="isAdmin"
                        no-action
                        v-model="expandSettings"
          >
            <template v-slot:prependIcon>
              <v-badge
                dot
                inline
                :value="$store.getters.getUnreadAnnouncementsCount()"
                color="info"
              >
                <v-icon>mdi-cog</v-icon>
              </v-badge>
            </template>
            <template v-slot:activator>
              <v-list-item-title>{{ $t('server.tab_title') }}</v-list-item-title>
            </template>

            <v-list-item :to="{name: 'settings-users'}">
              <v-list-item-title>{{ $t('users.users') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'settings-server'}">
              <v-list-item-title>{{ $t('common.settings') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'settings-ui'}">
              <v-list-item-title>{{ $t('common.ui') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'metrics'}">
              <v-list-item-title>{{ $t('metrics.title') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'announcements'}">
              <v-badge
                dot
                inline
                :value="$store.getters.getUnreadAnnouncementsCount()"
                color="info"
              >
                <v-list-item-title>{{ $t('announcements.tab_title') }}</v-list-item-title>
              </v-badge>
            </v-list-item>

            <v-list-item :to="{name: 'updates'}">
              <v-badge
                dot
                inline
                :value="$store.getters.isLatestVersion() == 0"
                color="warning"
              >
                <v-list-item-title>{{ $t('server.updates') }}</v-list-item-title>
              </v-badge>
            </v-list-item>
          </v-list-group>

          <!--   ACCOUNT     -->
          <v-list-group prepend-icon="mdi-account"
                        no-action
                        v-model="expandAccount"
          >
            <template v-slot:activator>
              <v-list-item-title>{{ $t('account_settings.my_account') }}</v-list-item-title>
            </template>

            <v-list-item :to="{name: 'account-me'}">
              <v-list-item-title>{{ $t('account_settings.details') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'account-api-keys'}">
              <v-list-item-title>{{ $t('users.api_keys') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'account-settings-ui'}">
              <v-list-item-title>{{ $t('common.ui') }}</v-list-item-title>
            </v-list-item>

            <v-list-item :to="{name: 'account-activity'}">
              <v-list-item-title>{{ $t('users.authentication_activity') }}</v-list-item-title>
            </v-list-item>
          </v-list-group>

          <v-list-item @click="logout">
            <v-list-item-icon>
              <v-icon>mdi-power</v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title>{{ $t('navigation.logout') }}</v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </v-list>

        <v-divider/>

        <v-list dense class="mt-2">
          <v-list-item>
            <v-list-item-icon>
              <v-icon>{{ themeIcon }}</v-icon>
            </v-list-item-icon>
            <v-select
              class="py-2"
              dense
              v-model="theme"
              :items="themes"
              :label="$t('home.theme')"
            ></v-select>
          </v-list-item>

          <v-list-item>
            <v-list-item-icon>
              <v-icon>mdi-translate</v-icon>
            </v-list-item-icon>
            <v-select
              dense
              class="py-2"
              v-model="locale"
              :items="locales"
              :label="$t('home.translation')"
            >
            </v-select>
          </v-list-item>
        </v-list>

        <v-spacer/>
      </template>

      <template v-slot:append>
        <div v-if="isAdmin && !$_.isEmpty($store.state.actuatorInfo)"
             class="pa-2 pb-6 text-caption"
        >
          <v-badge
            dot
            :value="$store.getters.isLatestVersion() == 0"
            color="warning"
          >
            <router-link :to="{name: 'updates'}" class="link-none">
              v{{ $store.state.actuatorInfo.build.version }}-{{ $store.state.actuatorInfo.git.branch }}
            </router-link>
          </v-badge>
        </div>
      </template>
    </v-navigation-drawer>

    <v-main class="fill-height">
      <reusable-dialogs/>
      <toaster-notification/>
      <router-view/>
    </v-main>
  </div>
</template>

<script lang="ts">
import ReusableDialogs from '@/components/ReusableDialogs.vue'
import LibraryActionsMenu from '@/components/menus/LibraryActionsMenu.vue'
import SearchBox from '@/components/SearchBox.vue'
import {Theme} from '@/types/themes'
import Vue from 'vue'
import {LIBRARIES_ALL} from '@/types/library'
import ToasterNotification from '@/components/ToasterNotification.vue'
import {MediaStatus} from '@/types/enum-books'
import {LibraryDto} from '@/types/komga-libraries'
import {BookSearch, SearchConditionAnyOfBook, SearchConditionMediaStatus, SearchOperatorIs} from '@/types/komga-search'
import LibrariesActionsMenu from '@/components/menus/LibrariesActionsMenu.vue'
import ReorderLibraries from '@/components/ReorderLibraries.vue'

export default Vue.extend({
  name: 'HomeView',
  components: {
    ReorderLibraries,
    LibrariesActionsMenu,
    ToasterNotification,
    LibraryActionsMenu,
    SearchBox,
    ReusableDialogs,
  },
  data: function () {
    return {
      LIBRARIES_ALL,
      drawerVisible: this.$vuetify.breakpoint.lgAndUp,
      locales: this.$i18n.availableLocales.map((x: any) => ({text: this.$i18n.t('common.locale_name', x), value: x})),
      expandSettings: false,
      expandDuplicatePages: false,
      expandMediaManagement: false,
      expandImport: false,
      expandAccount: false,
      expandUnpinned: false,
      showReorder: false,
    }
  },
  async created() {
    if (this.isAdmin) {
      this.$actuator.getInfo()
        .then(x => this.$store.commit('setActuatorInfo', x))
      this.$komgaBooks.getBooksList({
        condition: new SearchConditionAnyOfBook([
          new SearchConditionMediaStatus(new SearchOperatorIs(MediaStatus.ERROR)),
          new SearchConditionMediaStatus(new SearchOperatorIs(MediaStatus.UNSUPPORTED)),
        ]),
      } as BookSearch, {size: 0} as PageRequest)
        .then(x => this.$store.commit('setBooksToCheck', x.totalElements))
      this.$komgaAnnouncements.getAnnouncements()
        .then(x => this.$store.commit('setAnnouncements', x))
      this.$komgaReleases.getReleases()
        .then(x => this.$store.commit('setReleases', x))
    }
    this.checkRoute(this.$route)
  },
  watch: {
    $route(to, from) {
      this.checkRoute(to)
    },
  },
  computed: {
    taskCount(): number {
      return this.$store.state.komgaSse.taskCount
    },
    taskCountByType(): { [key: string]: number } {
      return this.$store.state.komgaSse.taskCountByType
    },
    libraries(): LibraryDto[] {
      return this.$store.getters.getLibraries
    },
    librariesPinned(): LibraryDto[] {
      return this.$store.getters.getLibrariesPinned
    },
    librariesUnpinned(): LibraryDto[] {
      return this.$store.getters.getLibrariesUnpinned
    },
    isAdmin(): boolean {
      return this.$store.getters.meAdmin
    },
    themes(): object[] {
      return [
        {text: this.$i18n.t(Theme.LIGHT), value: Theme.LIGHT},
        {text: this.$i18n.t(Theme.DARK), value: Theme.DARK},
        {text: this.$i18n.t(Theme.SYSTEM), value: Theme.SYSTEM},
      ]
    },
    themeIcon(): string {
      switch (this.theme) {
        case Theme.LIGHT:
          return 'mdi-brightness-7'
        case Theme.DARK:
          return 'mdi-brightness-3'
        case Theme.SYSTEM:
          return 'mdi-brightness-auto'
      }
      return ''
    },

    theme: {
      get: function (): Theme {
        return this.$store.state.persistedState.theme
      },
      set: function (theme: Theme): void {
        if (Object.values(Theme).includes(theme)) {
          this.$store.commit('setTheme', theme)
        }
      },
    },
    locale: {
      get: function (): string {
        return this.$i18n.locale
      },
      set: function (locale: string): void {
        if (this.$i18n.availableLocales.includes(locale)) {
          this.$store.commit('setLocale', locale)
        }
      },
    },
  },
  methods: {
    checkRoute(to) {
      this.expandSettings = to.path.includes('/settings/')
      this.expandMediaManagement = to.path.includes('/media-management/')
      this.expandImport = to.path.includes('/import/')
      this.expandDuplicatePages = to.path.includes('/duplicate-pages/')
      this.expandAccount = to.path.includes('/account/')
      if (this.librariesUnpinned.some(it => it.id === to.params.libraryId)) this.expandUnpinned = true
      else if (this.librariesPinned.some(it => it.id === to.params.libraryId)) this.expandUnpinned = false
    },
    toggleDrawer() {
      this.drawerVisible = !this.drawerVisible
    },
    logout() {
      this.$store.dispatch('logout')
      this.$router.push({name: 'login', query: {'logout': true}})
    },
    addLibrary() {
      this.$store.dispatch('dialogAddLibrary')
    },
  },
})
</script>

```
#### File: komga-webui/src/router.ts
- **Current Purpose**: Define application routes
- **Required Changes**:
  - Update route for HistoryView to point to ScanHistoryView
  - Add new route for PushToKindleProgressView
  - Update route names and paths accordingly
  - Ensure admin guards are properly applied


```python
import urls from '@/functions/urls'
import Vue from 'vue'
import Router from 'vue-router'
import store from './store'
import {LIBRARIES_ALL, LIBRARY_ROUTE} from '@/types/library'

const qs = require('qs')

Vue.use(Router)

const lStore = store as any

const adminGuard = (to: any, from: any, next: any) => {
  if (!lStore.getters.meAdmin) next({name: 'home'})
  else next()
}

const noLibraryGuard = (to: any, from: any, next: any) => {
  if (lStore.state.komgaLibraries.libraries.length === 0) {
    next({name: 'welcome'})
  } else next()
}

const noLibraryNorPinGuard = (to: any, from: any, next: any) => {
  if (lStore.state.komgaLibraries.libraries.length === 0) {
    next({name: 'welcome'})
  } else if (lStore.getters.getLibrariesPinned.length === 0) {
    next({name: 'no-pins'})
  } else next()
}

const getLibraryRoute = (libraryId: string) => {
  switch ((lStore.getters.getLibraryRoute(libraryId) as LIBRARY_ROUTE)) {
    case LIBRARY_ROUTE.COLLECTIONS:
      return 'browse-collections'
    case LIBRARY_ROUTE.READLISTS:
      return 'browse-readlists'
    case LIBRARY_ROUTE.BROWSE:
      return 'browse-libraries'
    case LIBRARY_ROUTE.BOOKS:
      return 'browse-books'
    case LIBRARY_ROUTE.RECOMMENDED:
    default:
      return libraryId === LIBRARIES_ALL ? 'browse-libraries' : 'recommended-libraries'
  }
}

const router = new Router({
  mode: 'history',
  base: urls.base,
  parseQuery(query: string) {
    return qs.parse(query)
  },
  stringifyQuery(query: Object) {
    const res = qs.stringify(query)
    return res ? `?${res}` : ''
  },
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: {name: 'dashboard'},
      component: () => import(/* webpackChunkName: "home" */ './views/HomeView.vue'),
      children: [
        {
          path: '/welcome',
          name: 'welcome',
          component: () => import(/* webpackChunkName: "welcome" */ './views/WelcomeView.vue'),
        },
        {
          path: '/no-pins',
          name: 'no-pins',
          component: () => import(/* webpackChunkName: "no-pins" */ './views/NoPinnedLibraries.vue'),
        },
        {
          path: '/dashboard',
          name: 'dashboard',
          beforeEnter: noLibraryNorPinGuard,
          component: () => import(/* webpackChunkName: "dashboard" */ './views/DashboardView.vue'),
        },
        {
          path: '/settings/users',
          name: 'settings-users',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-users" */ './views/SettingsUsers.vue'),
          children: [
            {
              path: '/settings/users/add',
              name: 'settings-users-add',
              component: () => import(/* webpackChunkName: "settings-user" */ './components/dialogs/UserAddDialog.vue'),
            },
          ],
        },
        {
          path: '/settings/server',
          name: 'settings-server',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-server" */ './views/SettingsServer.vue'),
        },
        {
          path: '/settings/ui',
          name: 'settings-ui',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "settings-ui" */ './views/UISettings.vue'),
        },
        {
          path: '/settings/metrics',
          name: 'metrics',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "metrics" */ './views/MetricsView.vue'),
        },
        {
          path: '/settings/announcements',
          name: 'announcements',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "announcements" */ './views/AnnouncementsView.vue'),
        },
        {
          path: '/settings/updates',
          name: 'updates',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "updates" */ './views/UpdatesView.vue'),
        },
        {
          path: '/media-management/analysis',
          name: 'media-analysis',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "media-analysis" */ './views/MediaAnalysis.vue'),
        },
        {
          path: '/media-management/missing-posters',
          name: 'missing-posters',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "missing-posters" */ './views/MissingPosters.vue'),
        },
        {
          path: '/media-management/duplicate-files',
          name: 'duplicate-files',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-files" */ './views/DuplicateFiles.vue'),
        },
        {
          path: '/media-management/duplicate-pages/known',
          name: 'settings-duplicate-pages-known',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-pages-known" */ './views/DuplicatePagesKnown.vue'),
        },
        {
          path: '/media-management/duplicate-pages/unknown',
          name: 'settings-duplicate-pages-unknown',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "duplicate-pages-new" */ './views/DuplicatePagesUnknown.vue'),
        },
        {
          path: '/history',
          name: 'history',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "history" */ './views/HistoryView.vue'),
        },
        {
          path: '/account/me',
          name: 'account-me',
          component: () => import(/* webpackChunkName: "account-me" */ './views/AccountView.vue'),
        },
        {
          path: '/account/api-keys',
          name: 'account-api-keys',
          component: () => import(/* webpackChunkName: "account-api-keys" */ './views/ApiKeys.vue'),
        },
        {
          path: '/account/settings-ui',
          name: 'account-settings-ui',
          component: () => import(/* webpackChunkName: "account-settings-ui" */ './views/UIUserSettings.vue'),
        },
        {
          path: '/account/authentication-activity',
          name: 'account-activity',
          component: () => import(/* webpackChunkName: "account-activity" */ './views/SelfAuthenticationActivity.vue'),
        },
        {
          path: '/libraries/:libraryId?',
          name: 'libraries',
          redirect: (route) => ({
            name: getLibraryRoute(route.params.libraryId || LIBRARIES_ALL),
            params: {libraryId: route.params.libraryId || LIBRARIES_ALL},
          }),
        },
        {
          path: '/libraries/:libraryId/recommended',
          name: 'recommended-libraries',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "dashboard" */ './views/DashboardView.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/books',
          name: 'browse-books',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-books" */ './views/BrowseBooks.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/series',
          name: 'browse-libraries',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-libraries" */ './views/BrowseLibraries.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/collections',
          name: 'browse-collections',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-collections" */ './views/BrowseCollections.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/libraries/:libraryId/readlists',
          name: 'browse-readlists',
          beforeEnter: noLibraryGuard,
          component: () => import(/* webpackChunkName: "browse-readlists" */ './views/BrowseReadLists.vue'),
          props: (route) => ({libraryId: route.params.libraryId}),
        },
        {
          path: '/collections/:collectionId',
          name: 'browse-collection',
          component: () => import(/* webpackChunkName: "browse-collection" */ './views/BrowseCollection.vue'),
          props: (route) => ({collectionId: route.params.collectionId}),
        },
        {
          path: '/readlists/:readListId',
          name: 'browse-readlist',
          component: () => import(/* webpackChunkName: "browse-readlist" */ './views/BrowseReadList.vue'),
          props: (route) => ({readListId: route.params.readListId}),
        },
        {
          path: '/series/:seriesId',
          name: 'browse-series',
          component: () => import(/* webpackChunkName: "browse-series" */ './views/BrowseSeries.vue'),
          props: (route) => ({seriesId: route.params.seriesId}),
        },
        {
          path: '/book/:bookId',
          name: 'browse-book',
          component: () => import(/* webpackChunkName: "browse-book" */ './views/BrowseBook.vue'),
          props: (route) => ({bookId: route.params.bookId}),
        },
        {
          path: '/oneshot/:seriesId',
          name: 'browse-oneshot',
          component: () => import(/* webpackChunkName: "browse-oneshot" */ './views/BrowseOneshot.vue'),
          props: (route) => ({seriesId: route.params.seriesId}),
        },
        {
          path: '/search',
          name: 'search',
          component: () => import(/* webpackChunkName: "search" */ './views/SearchView.vue'),
        },
        {
          path: '/import/books',
          name: 'import-books',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "import-books" */ './views/ImportBooks.vue'),
        },
        {
          path: '/import/readlist',
          name: 'import-readlist',
          beforeEnter: adminGuard,
          component: () => import(/* webpackChunkName: "import-readlist" */ './views/ImportReadList.vue'),
        },
      ],
    },
    {
      path: '/startup',
      name: 'startup',
      component: () => import(/* webpackChunkName: "startup" */ './views/StartupView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import(/* webpackChunkName: "login" */ './views/LoginView.vue'),
    },
    {
      path: '/book/:bookId/read',
      name: 'read-book',
      component: () => import(/* webpackChunkName: "read-book" */ './views/DivinaReader.vue'),
      props: (route) => ({bookId: route.params.bookId}),
    },
    {
      path: '/book/:bookId/read-epub',
      name: 'read-epub',
      component: () => import(/* webpackChunkName: "read-epub" */ './views/EpubReader.vue'),
      props: (route) => ({bookId: route.params.bookId}),
    },
    {
      path: '*',
      name: 'notfound',
      component: () => import(/* webpackChunkName: "notfound" */ './views/PageNotFound.vue'),
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      if (to.name !== from.name) {
        return {x: 0, y: 0}
      }
    }
  },
})

router.beforeEach((to, from, next) => {
  // avoid document.title flickering when changing route
  if (!['read-book', 'read-epub', 'browse-book', 'browse-oneshot', 'browse-series', 'browse-libraries', 'browse-books',
    'recommended-libraries', 'browse-collection', 'browse-collections', 'browse-readlist', 'browse-readlists'].includes(<string>to.name)
  ) {
    document.title = 'Komga'
  }

  if (window.opener !== null &&
    window.name === 'oauth2Login' &&
    to.query.server_redirect === 'Y'
  ) {
    if (!to.query.error) {
      // authentication succeeded, we redirect the parent window so that it can login via cookie
      window.opener.location.href = urls.origin
    } else {
      // authentication failed, we cascade the error message to the parent
      window.opener.location.href = window.location
    }
    // we can close the popup
    window.close()
  }

  if (to.name !== 'startup' && to.name !== 'login' && !lStore.getters.authenticated) {
    const query = Object.assign({}, to.query, {redirect: to.fullPath})
    next({name: 'startup', query: query})
  } else next()
})

export default router

```
#### File: komga-webui/src/services/kindle-log.service.ts (NEW)
- **Purpose**: Handle API communication for Kindle logs
- **Requirements**:
  - Method to fetch logs from backend API
  - Method to clear logs from backend API
  - Proper error handling and typing
  - Axios-based HTTP client integration

### Backend Files

#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/BookController.kt
- **Current Purpose**: Handle book-related API endpoints
- **Required Changes**:
  - Modify pushToKindle method to capture and store logs
  - Add unique job ID for each push operation
  - Store logs in memory or temporary storage
  - Return job ID in response


```python
package org.gotson.komga.interfaces.api.rest

import io.github.oshai.kotlinlogging.KotlinLogging
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.Parameter
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import jakarta.servlet.http.HttpServletRequest
import jakarta.validation.Valid
import org.gotson.komga.application.tasks.HIGHEST_PRIORITY
import org.gotson.komga.application.tasks.HIGH_PRIORITY
import org.gotson.komga.application.tasks.LOWEST_PRIORITY
import org.gotson.komga.application.tasks.TaskEmitter
import org.gotson.komga.domain.model.BookSearch
import org.gotson.komga.domain.model.Dimension
import org.gotson.komga.domain.model.DomainEvent
import org.gotson.komga.domain.model.ImageConversionException
import org.gotson.komga.domain.model.MarkSelectedPreference
import org.gotson.komga.domain.model.Media
import org.gotson.komga.domain.model.MediaExtensionEpub
import org.gotson.komga.domain.model.MediaNotReadyException
import org.gotson.komga.domain.model.MediaProfile
import org.gotson.komga.domain.model.ReadStatus
import org.gotson.komga.domain.model.SearchCondition
import org.gotson.komga.domain.model.SearchContext
import org.gotson.komga.domain.model.SearchOperator
import org.gotson.komga.domain.model.ThumbnailBook
import org.gotson.komga.domain.persistence.BookMetadataRepository
import org.gotson.komga.domain.persistence.BookRepository
import org.gotson.komga.domain.persistence.MediaRepository
import org.gotson.komga.domain.persistence.ReadListRepository
import org.gotson.komga.domain.persistence.ThumbnailBookRepository
import org.gotson.komga.domain.service.BookAnalyzer
import org.gotson.komga.domain.service.BookLifecycle
import org.gotson.komga.infrastructure.image.ImageAnalyzer
import org.gotson.komga.infrastructure.jooq.UnpagedSorted
import org.gotson.komga.infrastructure.mediacontainer.ContentDetector
import org.gotson.komga.infrastructure.openapi.OpenApiConfiguration
import org.gotson.komga.infrastructure.openapi.PageableAsQueryParam
import org.gotson.komga.infrastructure.openapi.PageableWithoutSortAsQueryParam
import org.gotson.komga.infrastructure.security.KomgaPrincipal
import org.gotson.komga.infrastructure.web.getMediaTypeOrDefault
import org.gotson.komga.interfaces.api.CommonBookController
import org.gotson.komga.interfaces.api.ContentRestrictionChecker
import org.gotson.komga.interfaces.api.WebPubGenerator
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_DIVINA_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_POSITION_LIST_JSON
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_POSITION_LIST_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.MEDIATYPE_WEBPUB_JSON_VALUE
import org.gotson.komga.interfaces.api.dto.WPPublicationDto
import org.gotson.komga.interfaces.api.getBookLastModified
import org.gotson.komga.interfaces.api.persistence.BookDtoRepository
import org.gotson.komga.interfaces.api.rest.dto.BookDto
import org.gotson.komga.interfaces.api.rest.dto.BookImportBatchDto
import org.gotson.komga.interfaces.api.rest.dto.BookMetadataUpdateDto
import org.gotson.komga.interfaces.api.rest.dto.PageDto
import org.gotson.komga.interfaces.api.rest.dto.R2Positions
import org.gotson.komga.interfaces.api.rest.dto.ReadListDto
import org.gotson.komga.interfaces.api.rest.dto.ReadProgressUpdateDto
import org.gotson.komga.interfaces.api.rest.dto.ThumbnailBookDto
import org.gotson.komga.interfaces.api.rest.dto.patch
import org.gotson.komga.interfaces.api.rest.dto.restrictUrl
import org.gotson.komga.interfaces.api.rest.dto.toDto
import org.gotson.komga.interfaces.api.setNotModified
import org.springframework.context.ApplicationEventPublisher
import org.springframework.data.domain.Page
import org.springframework.data.domain.PageRequest
import org.springframework.data.domain.Pageable
import org.springframework.data.domain.Sort
import org.springframework.format.annotation.DateTimeFormat
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.security.core.annotation.AuthenticationPrincipal
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PatchMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestHeader
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.context.request.ServletWebRequest
import org.springframework.web.context.request.WebRequest
import org.springframework.web.multipart.MultipartFile
import org.springframework.web.server.ResponseStatusException
import java.lang.ProcessBuilder
import java.nio.file.NoSuchFileException
import java.time.LocalDate
import java.time.ZoneOffset

private val logger = KotlinLogging.logger {}

@RestController
@RequestMapping(produces = [MediaType.APPLICATION_JSON_VALUE])
class BookController(
  private val taskEmitter: TaskEmitter,
  private val bookAnalyzer: BookAnalyzer,
  private val bookLifecycle: BookLifecycle,
  private val bookRepository: BookRepository,
  private val bookMetadataRepository: BookMetadataRepository,
  private val mediaRepository: MediaRepository,
  private val bookDtoRepository: BookDtoRepository,
  private val readListRepository: ReadListRepository,
  private val contentDetector: ContentDetector,
  private val imageAnalyzer: ImageAnalyzer,
  private val eventPublisher: ApplicationEventPublisher,
  private val thumbnailBookRepository: ThumbnailBookRepository,
  private val webPubGenerator: WebPubGenerator,
  private val contentRestrictionChecker: ContentRestrictionChecker,
  private val commonBookController: CommonBookController,
) {
  @Deprecated("use /v1/books/list instead")
  @PageableAsQueryParam
  @GetMapping("api/v1/books")
  @Operation(summary = "List books", description = "Use POST /api/v1/books/list instead. Deprecated since 1.19.0.", tags = [OpenApiConfiguration.TagNames.BOOKS, OpenApiConfiguration.TagNames.DEPRECATED])
  fun getAllBooksDeprecated(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "search", required = false) searchTerm: String? = null,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @RequestParam(name = "media_status", required = false) mediaStatus: List<Media.Status>? = null,
    @RequestParam(name = "read_status", required = false) readStatus: List<ReadStatus>? = null,
    @RequestParam(name = "released_after", required = false)
    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
    releasedAfter: LocalDate? = null,
    @RequestParam(name = "tag", required = false) tags: List<String>? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !searchTerm.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    val bookSearch =
      BookSearch(
        SearchCondition.AllOfBook(
          buildList {
            if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfBook(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
            if (!mediaStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(mediaStatus.map { SearchCondition.MediaStatus(SearchOperator.Is(it)) }))
            if (!readStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(readStatus.map { SearchCondition.ReadStatus(SearchOperator.Is(it)) }))
            if (!tags.isNullOrEmpty()) add(SearchCondition.AnyOfBook(tags.map { SearchCondition.Tag(SearchOperator.Is(it)) }))
            releasedAfter?.let { add(SearchCondition.ReleaseDate(SearchOperator.After(it.atStartOfDay(ZoneOffset.UTC)))) }
          },
        ),
        searchTerm,
      )

    return bookDtoRepository
      .findAll(bookSearch, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @PageableAsQueryParam
  @PostMapping("api/v1/books/list")
  @Operation(summary = "List books", tags = [OpenApiConfiguration.TagNames.BOOKS])
  fun getBooks(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestBody search: BookSearch,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !search.fullTextSearch.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository
      .findAll(search, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List latest books", description = "Return newly added or updated books.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableWithoutSortAsQueryParam
  @GetMapping("api/v1/books/latest")
  fun getBooksLatest(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort = Sort.by(Sort.Order.desc("lastModifiedDate"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository
      .findAll(
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List books on deck", description = "Return first unread book of series with at least one book read and no books in progress.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableWithoutSortAsQueryParam
  @GetMapping("api/v1/books/ondeck")
  fun getBooksOnDeck(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> =
    bookDtoRepository
      .findAllOnDeck(
        principal.user.id,
        principal.user.getAuthorizedLibraryIds(libraryIds),
        page,
        principal.user.restrictions,
      ).map { it.restrictUrl(!principal.user.isAdmin) }

  @Operation(summary = "List duplicate books", description = "Return books that have the same file hash.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PageableAsQueryParam
  @GetMapping("api/v1/books/duplicates")
  @PreAuthorize("hasRole('ADMIN')")
  fun getBooksDuplicates(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        else -> Sort.by(Sort.Order.asc("fileHash"))
      }

    val pageRequest =
      if (unpaged)
        Pageable.unpaged()
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return bookDtoRepository.findAllDuplicates(principal.user.id, pageRequest)
  }

  @Operation(summary = "Get book details", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}")
  fun getBookById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto =
    bookDtoRepository.findByIdOrNull(bookId, principal.user.id)?.let {
      contentRestrictionChecker.checkContentRestriction(principal.user, it)

      it.restrictUrl(!principal.user.isAdmin)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get previous book in series", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/previous")
  fun getBookSiblingPrevious(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookDtoRepository
      .findPreviousInSeriesOrNull(bookId, principal.user.id)
      ?.restrictUrl(!principal.user.isAdmin)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Get next book in series", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/next")
  fun getBookSiblingNext(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): BookDto {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookDtoRepository
      .findNextInSeriesOrNull(bookId, principal.user.id)
      ?.restrictUrl(!principal.user.isAdmin)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book's readlists", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @GetMapping("api/v1/books/{bookId}/readlists")
  fun getReadListsByBookId(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
  ): List<ReadListDto> {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return readListRepository
      .findAllContainingBookId(bookId, principal.user.getAuthorizedLibraryIds(null), principal.user.restrictions)
      .map { it.toDto() }
  }

  @Operation(summary = "Get book's poster image", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/thumbnail"],
    produces = [MediaType.IMAGE_JPEG_VALUE],
  )
  fun getBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ByteArray {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookLifecycle.getThumbnailBytes(bookId)?.bytes ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Get book poster image", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(value = ["api/v1/books/{bookId}/thumbnails/{thumbnailId}"], produces = [MediaType.IMAGE_JPEG_VALUE])
  fun getBookThumbnailById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ): ByteArray {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return bookLifecycle.getThumbnailBytesByThumbnailId(thumbnailId)?.bytes
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book posters", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @GetMapping(value = ["api/v1/books/{bookId}/thumbnails"], produces = [MediaType.APPLICATION_JSON_VALUE])
  fun getBookThumbnails(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
  ): Collection<ThumbnailBookDto> {
    contentRestrictionChecker.checkContentRestriction(principal.user, bookId)

    return thumbnailBookRepository
      .findAllByBookId(bookId)
      .map { it.toDto() }
  }

  @Operation(summary = "Add book poster", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PostMapping(value = ["api/v1/books/{bookId}/thumbnails"], consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
  @PreAuthorize("hasRole('ADMIN')")
  fun addUserUploadedBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @RequestParam("file") file: MultipartFile,
    @RequestParam("selected") selected: Boolean = true,
  ): ThumbnailBookDto {
    val book = bookRepository.findByIdOrNull(bookId) ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

    val mediaType = file.inputStream.buffered().use { contentDetector.detectMediaType(it) }
    if (!contentDetector.isImage(mediaType))
      throw ResponseStatusException(HttpStatus.UNSUPPORTED_MEDIA_TYPE)

    return bookLifecycle
      .addThumbnailForBook(
        ThumbnailBook(
          bookId = book.id,
          thumbnail = file.bytes,
          type = ThumbnailBook.Type.USER_UPLOADED,
          selected = selected,
          fileSize = file.bytes.size.toLong(),
          mediaType = mediaType,
          dimension = imageAnalyzer.getDimension(file.inputStream.buffered()) ?: Dimension(0, 0),
        ),
        if (selected) MarkSelectedPreference.YES else MarkSelectedPreference.NO,
      ).toDto()
  }

  @Operation(summary = "Mark book poster as selected", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PutMapping("api/v1/books/{bookId}/thumbnails/{thumbnailId}/selected")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun markBookThumbnailSelected(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    thumbnailBookRepository.findByIdOrNull(thumbnailId)?.let {
      thumbnailBookRepository.markSelected(it)
      eventPublisher.publishEvent(DomainEvent.ThumbnailBookAdded(it.copy(selected = true)))
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Delete book poster", description = "Only uploaded posters can be deleted.", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @DeleteMapping("api/v1/books/{bookId}/thumbnails/{thumbnailId}")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteUserUploadedBookThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "bookId") bookId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    thumbnailBookRepository.findByIdOrNull(thumbnailId)?.let {
      try {
        bookLifecycle.deleteThumbnailForBook(it)
      } catch (e: IllegalArgumentException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, e.message)
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List book pages", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @GetMapping("api/v1/books/{bookId}/pages")
  fun getBookPages(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): List<PageDto> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val media = mediaRepository.findById(book.id)
      when (media.status) {
        Media.Status.UNKNOWN -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book has not been analyzed yet")
        Media.Status.OUTDATED -> throw ResponseStatusException(
          HttpStatus.NOT_FOUND,
          "Book is outdated and must be re-analyzed",
        )

        Media.Status.ERROR -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book analysis failed")
        Media.Status.UNSUPPORTED -> throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book format is not supported")
        Media.Status.READY -> {
          val pages = if (media.profile == MediaProfile.PDF) bookAnalyzer.getPdfPagesDynamic(media) else media.pages
          pages.mapIndexed { index, bookPage ->
            PageDto(
              number = index + 1,
              fileName = bookPage.fileName,
              mediaType = bookPage.mediaType,
              width = bookPage.dimension?.width,
              height = bookPage.dimension?.height,
              sizeBytes = bookPage.fileSize,
            )
          }
        }
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book page image", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @ApiResponse(content = [Content(mediaType = "image/*", schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/pages/{pageNumber}"],
    produces = [MediaType.ALL_VALUE],
  )
  @PreAuthorize("hasRole('PAGE_STREAMING')")
  fun getBookPageByNumber(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    request: ServletWebRequest,
    @PathVariable bookId: String,
    @PathVariable pageNumber: Int,
    @Parameter(
      description = "Convert the image to the provided format.",
      schema = Schema(allowableValues = ["jpeg", "png"]),
    )
    @RequestParam(value = "convert", required = false)
    convertTo: String?,
    @Parameter(description = "If set to true, pages will start at index 0. If set to false, pages will start at index 1.")
    @RequestParam(value = "zero_based", defaultValue = "false")
    zeroBasedIndex: Boolean,
    @Parameter(description = "Some very limited server driven content negotiation is handled. If a book is a PDF book, and the Accept header contains 'application/pdf' as a more specific type than other 'image/' types, a raw PDF page will be returned.")
    @RequestHeader(HttpHeaders.ACCEPT, required = false)
    acceptHeaders: MutableList<MediaType>?,
    @RequestParam(value = "contentNegotiation", defaultValue = "true")
    contentNegotiation: Boolean,
  ): ResponseEntity<ByteArray> = commonBookController.getBookPageInternal(bookId, if (zeroBasedIndex) pageNumber + 1 else pageNumber, convertTo, request, principal, if (contentNegotiation) acceptHeaders else null)

  @Operation(summary = "Get book page thumbnail", description = "The image is resized to 300px on the largest dimension.", tags = [OpenApiConfiguration.TagNames.BOOK_PAGES])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(
    value = ["api/v1/books/{bookId}/pages/{pageNumber}/thumbnail"],
    produces = [MediaType.IMAGE_JPEG_VALUE],
  )
  fun getBookPageThumbnailByNumber(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    request: WebRequest,
    @PathVariable bookId: String,
    @PathVariable pageNumber: Int,
  ): ResponseEntity<ByteArray> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      val media = mediaRepository.findById(bookId)
      if (request.checkNotModified(getBookLastModified(media))) {
        return@let ResponseEntity
          .status(HttpStatus.NOT_MODIFIED)
          .setNotModified(media)
          .body(ByteArray(0))
      }

      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      try {
        val pageContent = bookLifecycle.getBookPage(book, pageNumber, resizeTo = 300)

        ResponseEntity
          .ok()
          .contentType(getMediaTypeOrDefault(pageContent.mediaType))
          .setNotModified(media)
          .body(pageContent.bytes)
      } catch (ex: IndexOutOfBoundsException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, "Page number does not exist")
      } catch (ex: ImageConversionException) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, ex.message)
      } catch (ex: MediaNotReadyException) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book analysis failed")
      } catch (ex: NoSuchFileException) {
        logger.warn(ex) { "File not found: $book" }
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "File not found, it may have moved")
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book's WebPub manifest", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE, MEDIATYPE_DIVINA_JSON_VALUE],
  )
  fun getBookWebPubManifest(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ResponseEntity<WPPublicationDto> {
    val manifest = commonBookController.getWebPubManifestInternal(principal, bookId, webPubGenerator)
    return ResponseEntity
      .ok()
      .contentType(manifest.mediaType)
      .body(manifest)
  }

  @Operation(summary = "List book's positions", description = "The Positions API is a proposed standard for OPDS 2 and Readium. It is used by the Epub Reader.", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/positions"],
    produces = [MEDIATYPE_POSITION_LIST_JSON_VALUE],
  )
  fun getBookPositions(
    request: HttpServletRequest,
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): ResponseEntity<R2Positions> =
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      val media = mediaRepository.findById(book.id)

      if (ServletWebRequest(request).checkNotModified(getBookLastModified(media))) {
        return ResponseEntity
          .status(HttpStatus.NOT_MODIFIED)
          .setNotModified(media)
          .body(null)
      }

      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val extension =
        mediaRepository.findExtensionByIdOrNull(book.id) as? MediaExtensionEpub
          ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

      ResponseEntity
        .ok()
        .contentType(MEDIATYPE_POSITION_LIST_JSON)
        .setNotModified(media)
        .body(R2Positions(extension.positions.size, extension.positions))
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get book's WebPub manifest (Epub)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/epub"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE],
  )
  fun getBookWebPubManifestEpub(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestEpubInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Get book's WebPub manifest (PDF)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/pdf"],
    produces = [MEDIATYPE_WEBPUB_JSON_VALUE],
  )
  fun getBookWebPubManifestPdf(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestPdfInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Get book's WebPub manifest (DiViNa)", tags = [OpenApiConfiguration.TagNames.BOOK_WEBPUB])
  @GetMapping(
    value = ["api/v1/books/{bookId}/manifest/divina"],
    produces = [MEDIATYPE_DIVINA_JSON_VALUE],
  )
  fun getBookWebPubManifestDivina(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable bookId: String,
  ): WPPublicationDto = commonBookController.getWebPubManifestDivinaInternal(principal, bookId, webPubGenerator)

  @Operation(summary = "Analyze book", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PostMapping("api/v1/books/{bookId}/analyze")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun bookAnalyze(
    @PathVariable bookId: String,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      taskEmitter.analyzeBook(book, HIGH_PRIORITY)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Refresh book metadata", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PostMapping("api/v1/books/{bookId}/metadata/refresh")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun bookRefreshMetadata(
    @PathVariable bookId: String,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      taskEmitter.refreshBookMetadata(book, priority = HIGH_PRIORITY)
      taskEmitter.refreshBookLocalArtwork(book, priority = HIGH_PRIORITY)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Update book metadata", description = "Set a field to null to unset the metadata. You can omit fields you don't want to update.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/{bookId}/metadata")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateBookMetadata(
    @PathVariable bookId: String,
    @Parameter(description = "Metadata fields to update. Set a field to null to unset the metadata. You can omit fields you don't want to update.")
    @Valid
    @RequestBody
    newMetadata: BookMetadataUpdateDto,
  ) = bookMetadataRepository.findByIdOrNull(bookId)?.let { existing ->
    val updated = existing.patch(newMetadata)
    bookMetadataRepository.update(updated)

    bookRepository.findByIdOrNull(bookId)?.let { updatedBook ->
      taskEmitter.aggregateSeriesMetadata(updatedBook.seriesId)
      updatedBook.let { eventPublisher.publishEvent(DomainEvent.BookUpdated(it)) }
    }
  } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Update book metadata in bulk", description = "Set a field to null to unset the metadata. You can omit fields you don't want to update.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/metadata")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateBookMetadataByBatch(
    @Parameter(description = "A map of book IDs which values are the metadata fields to update. Set a field to null to unset the metadata. You can omit fields you don't want to update.")
    @Valid
    @RequestBody
    newMetadatas: Map<String, BookMetadataUpdateDto>,
  ) {
    val updatedBooks =
      newMetadatas.mapNotNull { (bookId, newMetadata) ->
        bookMetadataRepository.findByIdOrNull(bookId)?.let { existing ->
          val updated = existing.patch(newMetadata)
          bookMetadataRepository.update(updated)

          bookRepository.findByIdOrNull(bookId)
        }
      }

    updatedBooks.forEach { eventPublisher.publishEvent(DomainEvent.BookUpdated(it)) }
    updatedBooks.map { it.seriesId }.distinct().forEach { taskEmitter.aggregateSeriesMetadata(it) }
  }

  @Operation(summary = "Mark book's read progress", description = "Mark book as read and/or change page progress.", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @PatchMapping("api/v1/books/{bookId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun markBookReadProgress(
    @PathVariable bookId: String,
    @Parameter(description = "page can be omitted if completed is set to true. completed can be omitted, and will be set accordingly depending on the page passed and the total number of pages in the book.")
    @Valid
    @RequestBody
    readProgress: ReadProgressUpdateDto,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      try {
        if (readProgress.completed != null && readProgress.completed)
          bookLifecycle.markReadProgressCompleted(book.id, principal.user)
        else
          bookLifecycle.markReadProgress(book, principal.user, readProgress.page!!)
      } catch (e: IllegalArgumentException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, e.message)
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Mark book as unread", description = "Mark book as unread", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @DeleteMapping("api/v1/books/{bookId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun deleteBookReadProgress(
    @PathVariable bookId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      bookLifecycle.deleteReadProgress(book, principal.user)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Import books", tags = [OpenApiConfiguration.TagNames.BOOK_IMPORT])
  @PostMapping("api/v1/books/import")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun importBooks(
    @RequestBody bookImportBatch: BookImportBatchDto,
  ) {
    bookImportBatch.books.forEach {
      try {
        taskEmitter.importBook(
          sourceFile = it.sourceFile,
          seriesId = it.seriesId,
          copyMode = bookImportBatch.copyMode,
          destinationName = it.destinationName,
          upgradeBookId = it.upgradeBookId,
          priority = HIGHEST_PRIORITY,
        )
      } catch (e: Exception) {
        logger.error(e) { "Error while creating import task for: $it" }
      }
    }
  }

  @Operation(summary = "Delete book file", tags = [OpenApiConfiguration.TagNames.BOOKS])
  @DeleteMapping("api/v1/books/{bookId}/file")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteBookFile(
    @PathVariable bookId: String,
  ) {
    taskEmitter.deleteBook(
      bookId = bookId,
      priority = HIGHEST_PRIORITY,
    )
  }

  @Operation(summary = "Regenerate books posters", tags = [OpenApiConfiguration.TagNames.BOOK_POSTER])
  @PutMapping("api/v1/books/thumbnails")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun booksRegenerateThumbnails(
    @RequestParam(name = "for_bigger_result_only", required = false) forBiggerResultOnly: Boolean = false,
  ) {
    taskEmitter.findBookThumbnailsToRegenerate(forBiggerResultOnly, LOWEST_PRIORITY)
  }

  @PostMapping("api/v1/books/{bookId}/push-to-kindle")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun pushToKindle(
    @PathVariable bookId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    bookRepository.findByIdOrNull(bookId)?.let { book ->
      contentRestrictionChecker.checkContentRestriction(principal.user, book)

      val media = mediaRepository.findById(book.id)
      if (media.status != Media.Status.READY) {
        throw ResponseStatusException(HttpStatus.NOT_FOUND, "Book is not ready")
      }

      try {
        val processBuilder = ProcessBuilder("python3", "/app/komga_custom/push_to_kindle.py", book.url.path)
        processBuilder.redirectErrorStream(true)
        val process = processBuilder.start()
        val reader = process.inputStream.bufferedReader()
        val output = reader.readText()
        logger.info { "Push to kindle script output: $output" }
        process.waitFor()
      } catch (e: Exception) {
        logger.error(e) { "Error while executing push to kindle script for book: $bookId" }
        throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error while executing push to kindle script")
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }
}

```
#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/SeriesController.kt
- **Current Purpose**: Handle series-related API endpoints
- **Required Changes**:
  - Modify pushToKindle method to capture and store logs
  - Add unique job ID for each push operation
  - Store logs in memory or temporary storage
  - Return job ID in response


```python
package org.gotson.komga.interfaces.api.rest

import io.github.oshai.kotlinlogging.KotlinLogging
import io.swagger.v3.oas.annotations.Operation
import io.swagger.v3.oas.annotations.Parameter
import io.swagger.v3.oas.annotations.Parameters
import io.swagger.v3.oas.annotations.enums.ParameterIn
import io.swagger.v3.oas.annotations.media.Content
import io.swagger.v3.oas.annotations.media.Schema
import io.swagger.v3.oas.annotations.responses.ApiResponse
import jakarta.validation.Valid
import org.apache.commons.compress.archivers.zip.Zip64Mode
import org.apache.commons.compress.archivers.zip.ZipArchiveEntry
import org.apache.commons.compress.archivers.zip.ZipArchiveOutputStream
import org.apache.commons.io.IOUtils
import org.gotson.komga.application.tasks.HIGHEST_PRIORITY
import org.gotson.komga.application.tasks.HIGH_PRIORITY
import org.gotson.komga.application.tasks.TaskEmitter
import org.gotson.komga.domain.model.AlternateTitle
import org.gotson.komga.domain.model.Author
import org.gotson.komga.domain.model.BookSearch
import org.gotson.komga.domain.model.Dimension
import org.gotson.komga.domain.model.DomainEvent
import org.gotson.komga.domain.model.KomgaUser
import org.gotson.komga.domain.model.MarkSelectedPreference
import org.gotson.komga.domain.model.Media
import org.gotson.komga.domain.model.MediaType.ZIP
import org.gotson.komga.domain.model.ReadStatus
import org.gotson.komga.domain.model.SearchCondition
import org.gotson.komga.domain.model.SearchContext
import org.gotson.komga.domain.model.SearchField
import org.gotson.komga.domain.model.SearchOperator
import org.gotson.komga.domain.model.SeriesMetadata
import org.gotson.komga.domain.model.SeriesSearch
import org.gotson.komga.domain.model.ThumbnailSeries
import org.gotson.komga.domain.model.WebLink
import org.gotson.komga.domain.persistence.BookRepository
import org.gotson.komga.domain.persistence.SeriesCollectionRepository
import org.gotson.komga.domain.persistence.SeriesMetadataRepository
import org.gotson.komga.domain.persistence.SeriesRepository
import org.gotson.komga.domain.persistence.ThumbnailSeriesRepository
import org.gotson.komga.domain.service.BookLifecycle
import org.gotson.komga.domain.service.SeriesLifecycle
import org.gotson.komga.infrastructure.image.ImageAnalyzer
import org.gotson.komga.infrastructure.jooq.UnpagedSorted
import org.gotson.komga.infrastructure.mediacontainer.ContentDetector
import org.gotson.komga.infrastructure.openapi.AuthorsAsQueryParam
import org.gotson.komga.infrastructure.openapi.OpenApiConfiguration
import org.gotson.komga.infrastructure.openapi.PageableAsQueryParam
import org.gotson.komga.infrastructure.openapi.PageableWithoutSortAsQueryParam
import org.gotson.komga.infrastructure.security.KomgaPrincipal
import org.gotson.komga.infrastructure.web.Authors
import org.gotson.komga.infrastructure.web.DelimitedPair
import org.gotson.komga.interfaces.api.ContentRestrictionChecker
import org.gotson.komga.interfaces.api.persistence.BookDtoRepository
import org.gotson.komga.interfaces.api.persistence.ReadProgressDtoRepository
import org.gotson.komga.interfaces.api.persistence.SeriesDtoRepository
import org.gotson.komga.interfaces.api.rest.dto.BookDto
import org.gotson.komga.interfaces.api.rest.dto.CollectionDto
import org.gotson.komga.interfaces.api.rest.dto.GroupCountDto
import org.gotson.komga.interfaces.api.rest.dto.SeriesDto
import org.gotson.komga.interfaces.api.rest.dto.SeriesMetadataUpdateDto
import org.gotson.komga.interfaces.api.rest.dto.TachiyomiReadProgressUpdateV2Dto
import org.gotson.komga.interfaces.api.rest.dto.TachiyomiReadProgressV2Dto
import org.gotson.komga.interfaces.api.rest.dto.ThumbnailSeriesDto
import org.gotson.komga.interfaces.api.rest.dto.restrictUrl
import org.gotson.komga.interfaces.api.rest.dto.toDto
import org.springframework.context.ApplicationEventPublisher
import org.springframework.core.io.FileSystemResource
import org.springframework.data.domain.Page
import org.springframework.data.domain.PageRequest
import org.springframework.data.domain.Pageable
import org.springframework.data.domain.Sort
import org.springframework.http.ContentDisposition
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.security.access.prepost.PreAuthorize
import org.springframework.security.core.annotation.AuthenticationPrincipal
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PatchMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.ResponseStatus
import org.springframework.web.bind.annotation.RestController
import org.springframework.web.multipart.MultipartFile
import org.springframework.web.server.ResponseStatusException
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody
import java.io.OutputStream
import java.lang.ProcessBuilder
import java.net.URI
import java.nio.charset.StandardCharsets.UTF_8
import java.time.ZoneOffset
import java.time.ZonedDateTime
import java.util.zip.Deflater

private val logger = KotlinLogging.logger {}

@RestController
@RequestMapping("api", produces = [MediaType.APPLICATION_JSON_VALUE])
class SeriesController(
  private val taskEmitter: TaskEmitter,
  private val seriesRepository: SeriesRepository,
  private val seriesLifecycle: SeriesLifecycle,
  private val seriesMetadataRepository: SeriesMetadataRepository,
  private val seriesDtoRepository: SeriesDtoRepository,
  private val bookLifecycle: BookLifecycle,
  private val bookRepository: BookRepository,
  private val bookDtoRepository: BookDtoRepository,
  private val collectionRepository: SeriesCollectionRepository,
  private val readProgressDtoRepository: ReadProgressDtoRepository,
  private val eventPublisher: ApplicationEventPublisher,
  private val contentDetector: ContentDetector,
  private val imageAnalyzer: ImageAnalyzer,
  private val thumbnailsSeriesRepository: ThumbnailSeriesRepository,
  private val contentRestrictionChecker: ContentRestrictionChecker,
) {
  @Operation(summary = "List series", description = "Use POST /api/v1/series/list instead. Deprecated since 1.19.0.", tags = [OpenApiConfiguration.TagNames.SERIES, OpenApiConfiguration.TagNames.DEPRECATED])
  @Deprecated("use /v1/series/list instead")
  @PageableAsQueryParam
  @AuthorsAsQueryParam
  @Parameters(
    Parameter(
      description = "Search by regex criteria, in the form: regex,field. Supported fields are TITLE and TITLE_SORT.",
      `in` = ParameterIn.QUERY,
      name = "search_regex",
      schema = Schema(type = "string"),
    ),
  )
  @GetMapping("v1/series")
  fun getSeriesDeprecated(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "search", required = false) searchTerm: String? = null,
    @Parameter(hidden = true)
    @DelimitedPair("search_regex")
    searchRegex: Pair<String, String>? = null,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @RequestParam(name = "collection_id", required = false) collectionIds: List<String>? = null,
    @RequestParam(name = "status", required = false) metadataStatus: List<SeriesMetadata.Status>? = null,
    @RequestParam(name = "read_status", required = false) readStatus: List<ReadStatus>? = null,
    @RequestParam(name = "publisher", required = false) publishers: List<String>? = null,
    @RequestParam(name = "language", required = false) languages: List<String>? = null,
    @RequestParam(name = "genre", required = false) genres: List<String>? = null,
    @RequestParam(name = "tag", required = false) tags: List<String>? = null,
    @RequestParam(name = "age_rating", required = false) ageRatings: List<String>? = null,
    @RequestParam(name = "release_year", required = false) releaseYears: List<String>? = null,
    @RequestParam(name = "sharing_label", required = false) sharingLabels: List<String>? = null,
    @RequestParam(name = "deleted", required = false) deleted: Boolean? = null,
    @RequestParam(name = "complete", required = false) complete: Boolean? = null,
    @RequestParam(name = "oneshot", required = false) oneshot: Boolean? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) @Authors authors: List<Author>? = null,
    @Parameter(hidden = true) page: Pageable,
  ): Page<SeriesDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !searchTerm.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    val seriesSearch =
      SeriesSearch(
        condition =
          SearchCondition.AllOfSeries(
            buildList {
              if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
              if (!collectionIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(collectionIds.map { SearchCondition.CollectionId(SearchOperator.Is(it)) }))
              if (!metadataStatus.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(metadataStatus.map { SearchCondition.SeriesStatus(SearchOperator.Is(it)) }))
              if (!publishers.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(publishers.map { SearchCondition.Publisher(SearchOperator.Is(it)) }))
              if (!languages.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(languages.map { SearchCondition.Language(SearchOperator.Is(it)) }))
              if (!genres.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(genres.map { SearchCondition.Genre(SearchOperator.Is(it)) }))
              if (!tags.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(tags.map { SearchCondition.Tag(SearchOperator.Is(it)) }))
              if (!readStatus.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(readStatus.map { SearchCondition.ReadStatus(SearchOperator.Is(it)) }))
              if (!authors.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(authors.map { SearchCondition.Author(SearchOperator.Is(SearchCondition.AuthorMatch(it.name, it.role))) }))
              if (!ageRatings.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(ageRatings.map { it.toIntOrNull()?.let { ageRating -> SearchCondition.AgeRating(SearchOperator.Is(ageRating)) } ?: SearchCondition.AgeRating(SearchOperator.IsNullT()) }))
              if (!releaseYears.isNullOrEmpty())
                add(
                  SearchCondition.AnyOfSeries(
                    releaseYears.mapNotNull { it.toIntOrNull() }.map { releaseYear ->
                      SearchCondition.AllOfSeries(
                        SearchCondition.ReleaseDate(SearchOperator.After(ZonedDateTime.of(releaseYear - 1, 12, 31, 12, 0, 0, 0, ZoneOffset.UTC))),
                        SearchCondition.ReleaseDate(SearchOperator.Before(ZonedDateTime.of(releaseYear + 1, 1, 1, 12, 0, 0, 0, ZoneOffset.UTC))),
                      )
                    },
                  ),
                )

              if (!sharingLabels.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(sharingLabels.map { SearchCondition.SharingLabel(SearchOperator.Is(it)) }))
              oneshot?.let { add(SearchCondition.OneShot(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              complete?.let { add(SearchCondition.Complete(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
            },
          ),
        fullTextSearch = searchTerm,
        regexSearch =
          searchRegex?.let {
            when (it.second.lowercase()) {
              "title" -> Pair(it.first, SearchField.TITLE)
              "title_sort" -> Pair(it.first, SearchField.TITLE_SORT)
              else -> null
            }
          },
      )

    return seriesDtoRepository
      .findAll(seriesSearch, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List series", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PageableAsQueryParam
  @PostMapping("v1/series/list")
  fun getSeries(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestBody search: SeriesSearch,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<SeriesDto> {
    val sort =
      when {
        page.sort.isSorted -> page.sort
        !search.fullTextSearch.isNullOrBlank() -> Sort.by("relevance")
        else -> Sort.unsorted()
      }

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return seriesDtoRepository
      .findAll(search, SearchContext(principal.user), pageRequest)
      .map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List series groups", description = "Use POST /api/v1/series/list/alphabetical-groups instead. Deprecated since 1.19.0.", tags = [OpenApiConfiguration.TagNames.SERIES, OpenApiConfiguration.TagNames.DEPRECATED])
  @Deprecated("use /v1/series/list/alphabetical-groups instead")
  @AuthorsAsQueryParam
  @Parameters(
    Parameter(
      description = "Search by regex criteria, in the form: regex,field. Supported fields are TITLE and TITLE_SORT.",
      `in` = ParameterIn.QUERY,
      name = "search_regex",
      schema = Schema(type = "string"),
    ),
  )
  @GetMapping("v1/series/alphabetical-groups")
  fun getSeriesAlphabeticalGroupsDeprecated(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "search", required = false) searchTerm: String?,
    @Parameter(hidden = true)
    @DelimitedPair("search_regex")
    searchRegex: Pair<String, String>?,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>?,
    @RequestParam(name = "collection_id", required = false) collectionIds: List<String>?,
    @RequestParam(name = "status", required = false) metadataStatus: List<SeriesMetadata.Status>?,
    @RequestParam(name = "read_status", required = false) readStatus: List<ReadStatus>?,
    @RequestParam(name = "publisher", required = false) publishers: List<String>?,
    @RequestParam(name = "language", required = false) languages: List<String>?,
    @RequestParam(name = "genre", required = false) genres: List<String>?,
    @RequestParam(name = "tag", required = false) tags: List<String>?,
    @RequestParam(name = "age_rating", required = false) ageRatings: List<String>?,
    @RequestParam(name = "release_year", required = false) releaseYears: List<String>?,
    @RequestParam(name = "sharing_label", required = false) sharingLabels: List<String>? = null,
    @RequestParam(name = "deleted", required = false) deleted: Boolean?,
    @RequestParam(name = "complete", required = false) complete: Boolean?,
    @RequestParam(name = "oneshot", required = false) oneshot: Boolean? = null,
    @Parameter(hidden = true) @Authors authors: List<Author>?,
    @Parameter(hidden = true) page: Pageable,
  ): List<GroupCountDto> {
    val seriesSearch =
      SeriesSearch(
        condition =
          SearchCondition.AllOfSeries(
            buildList {
              if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
              if (!collectionIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(collectionIds.map { SearchCondition.CollectionId(SearchOperator.Is(it)) }))
              if (!metadataStatus.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(metadataStatus.map { SearchCondition.SeriesStatus(SearchOperator.Is(it)) }))
              if (!publishers.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(publishers.map { SearchCondition.Publisher(SearchOperator.Is(it)) }))
              if (!languages.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(languages.map { SearchCondition.Language(SearchOperator.Is(it)) }))
              if (!genres.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(genres.map { SearchCondition.Genre(SearchOperator.Is(it)) }))
              if (!tags.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(tags.map { SearchCondition.Tag(SearchOperator.Is(it)) }))
              if (!readStatus.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(readStatus.map { SearchCondition.ReadStatus(SearchOperator.Is(it)) }))
              if (!authors.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(authors.map { SearchCondition.Author(SearchOperator.Is(SearchCondition.AuthorMatch(it.name, it.role))) }))
              if (!ageRatings.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(ageRatings.map { it.toIntOrNull()?.let { ageRating -> SearchCondition.AgeRating(SearchOperator.Is(ageRating)) } ?: SearchCondition.AgeRating(SearchOperator.IsNullT()) }))
              if (!releaseYears.isNullOrEmpty())
                add(
                  SearchCondition.AnyOfSeries(
                    releaseYears.mapNotNull { it.toIntOrNull() }.map { releaseYear ->
                      SearchCondition.AllOfSeries(
                        SearchCondition.ReleaseDate(SearchOperator.After(ZonedDateTime.of(releaseYear - 1, 12, 31, 12, 0, 0, 0, ZoneOffset.UTC))),
                        SearchCondition.ReleaseDate(SearchOperator.Before(ZonedDateTime.of(releaseYear + 1, 1, 1, 12, 0, 0, 0, ZoneOffset.UTC))),
                      )
                    },
                  ),
                )

              if (!sharingLabels.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(sharingLabels.map { SearchCondition.SharingLabel(SearchOperator.Is(it)) }))
              oneshot?.let { add(SearchCondition.OneShot(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              complete?.let { add(SearchCondition.Complete(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
            },
          ),
        fullTextSearch = searchTerm,
        regexSearch =
          searchRegex?.let {
            when (it.second.lowercase()) {
              "title" -> Pair(it.first, SearchField.TITLE)
              "title_sort" -> Pair(it.first, SearchField.TITLE_SORT)
              else -> null
            }
          },
      )

    return seriesDtoRepository.countByFirstCharacter(seriesSearch, SearchContext(principal.user))
  }

  @Operation(summary = "List series groups", description = "List series grouped by the first character of their sort title.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PostMapping("v1/series/list/alphabetical-groups")
  fun getSeriesAlphabeticalGroups(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestBody search: SeriesSearch,
  ): List<GroupCountDto> = seriesDtoRepository.countByFirstCharacter(search, SearchContext(principal.user))

  @Operation(summary = "List latest series", description = "Return recently added or updated series.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PageableWithoutSortAsQueryParam
  @GetMapping("v1/series/latest")
  fun getSeriesLatest(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>?,
    @RequestParam(name = "deleted", required = false) deleted: Boolean?,
    @RequestParam(name = "oneshot", required = false) oneshot: Boolean? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<SeriesDto> {
    val sort = Sort.by(Sort.Order.desc("lastModified"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return seriesDtoRepository
      .findAll(
        SeriesSearch(
          SearchCondition.AllOfSeries(
            buildList {
              if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
              deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              oneshot?.let { add(SearchCondition.OneShot(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
            },
          ),
        ),
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List new series", description = "Return newly added series.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PageableWithoutSortAsQueryParam
  @GetMapping("v1/series/new")
  fun getSeriesNew(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @RequestParam(name = "deleted", required = false) deleted: Boolean? = null,
    @RequestParam(name = "oneshot", required = false) oneshot: Boolean? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<SeriesDto> {
    val sort = Sort.by(Sort.Order.desc("created"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return seriesDtoRepository
      .findAll(
        SeriesSearch(
          SearchCondition.AllOfSeries(
            buildList {
              if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
              deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              oneshot?.let { add(SearchCondition.OneShot(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
            },
          ),
        ),
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List updated series", description = "Return recently updated series, but not newly added ones.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PageableWithoutSortAsQueryParam
  @GetMapping("v1/series/updated")
  fun getSeriesUpdated(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @RequestParam(name = "library_id", required = false) libraryIds: List<String>? = null,
    @RequestParam(name = "deleted", required = false) deleted: Boolean? = null,
    @RequestParam(name = "oneshot", required = false) oneshot: Boolean? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) page: Pageable,
  ): Page<SeriesDto> {
    val sort = Sort.by(Sort.Order.desc("lastModified"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    return seriesDtoRepository
      .findAllRecentlyUpdated(
        SeriesSearch(
          SearchCondition.AllOfSeries(
            buildList {
              if (!libraryIds.isNullOrEmpty()) add(SearchCondition.AnyOfSeries(libraryIds.map { SearchCondition.LibraryId(SearchOperator.Is(it)) }))
              deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
              oneshot?.let { add(SearchCondition.OneShot(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
            },
          ),
        ),
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "Get series details", tags = [OpenApiConfiguration.TagNames.SERIES])
  @GetMapping("v1/series/{seriesId}")
  fun getSeriesById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") id: String,
  ): SeriesDto =
    seriesDtoRepository.findByIdOrNull(id, principal.user.id)?.let {
      contentRestrictionChecker.checkContentRestriction(principal.user, it)
      it.restrictUrl(!principal.user.isAdmin)
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Get series' poster image", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(value = ["v1/series/{seriesId}/thumbnail"], produces = [MediaType.IMAGE_JPEG_VALUE])
  fun getSeriesThumbnail(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") seriesId: String,
  ): ByteArray {
    principal.user.checkContentRestriction(seriesId)

    return seriesLifecycle.getThumbnailBytes(seriesId, principal.user.id)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Get series poster image", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @ApiResponse(content = [Content(schema = Schema(type = "string", format = "binary"))])
  @GetMapping(value = ["v1/series/{seriesId}/thumbnails/{thumbnailId}"], produces = [MediaType.IMAGE_JPEG_VALUE])
  fun getSeriesThumbnailById(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") seriesId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ): ByteArray {
    principal.user.checkContentRestriction(seriesId)

    return seriesLifecycle.getThumbnailBytesByThumbnailId(thumbnailId)
      ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List series posters", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @GetMapping(value = ["v1/series/{seriesId}/thumbnails"], produces = [MediaType.APPLICATION_JSON_VALUE])
  fun getSeriesThumbnails(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") seriesId: String,
  ): Collection<ThumbnailSeriesDto> {
    principal.user.checkContentRestriction(seriesId)

    return thumbnailsSeriesRepository
      .findAllBySeriesId(seriesId)
      .map { it.toDto() }
  }

  @Operation(summary = "Add series poster", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @PostMapping(value = ["v1/series/{seriesId}/thumbnails"], consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
  @PreAuthorize("hasRole('ADMIN')")
  fun addUserUploadedSeriesThumbnail(
    @PathVariable(name = "seriesId") seriesId: String,
    @RequestParam("file") file: MultipartFile,
    @RequestParam("selected") selected: Boolean = true,
  ): ThumbnailSeriesDto {
    val series = seriesRepository.findByIdOrNull(seriesId) ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
    if (series.oneshot) throw ResponseStatusException(HttpStatus.BAD_REQUEST)

    val mediaType = file.inputStream.buffered().use { contentDetector.detectMediaType(it) }
    if (!contentDetector.isImage(mediaType))
      throw ResponseStatusException(HttpStatus.UNSUPPORTED_MEDIA_TYPE)

    return seriesLifecycle
      .addThumbnailForSeries(
        ThumbnailSeries(
          seriesId = series.id,
          thumbnail = file.bytes,
          type = ThumbnailSeries.Type.USER_UPLOADED,
          fileSize = file.bytes.size.toLong(),
          mediaType = mediaType,
          dimension = imageAnalyzer.getDimension(file.inputStream.buffered()) ?: Dimension(0, 0),
        ),
        if (selected) MarkSelectedPreference.YES else MarkSelectedPreference.NO,
      ).toDto()
  }

  @Operation(summary = "Mark series poster as selected", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @PutMapping("v1/series/{seriesId}/thumbnails/{thumbnailId}/selected")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun markSeriesThumbnailSelected(
    @PathVariable(name = "seriesId") seriesId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    seriesRepository.findByIdOrNull(seriesId) ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
    thumbnailsSeriesRepository.findByIdOrNull(thumbnailId)?.let {
      thumbnailsSeriesRepository.markSelected(it)
      eventPublisher.publishEvent(DomainEvent.ThumbnailSeriesAdded(it.copy(selected = true)))
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "Delete series poster", tags = [OpenApiConfiguration.TagNames.SERIES_POSTER])
  @DeleteMapping("v1/series/{seriesId}/thumbnails/{thumbnailId}")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteUserUploadedSeriesThumbnail(
    @PathVariable(name = "seriesId") seriesId: String,
    @PathVariable(name = "thumbnailId") thumbnailId: String,
  ) {
    seriesRepository.findByIdOrNull(seriesId) ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
    thumbnailsSeriesRepository.findByIdOrNull(thumbnailId)?.let {
      try {
        seriesLifecycle.deleteThumbnailForSeries(it)
      } catch (e: IllegalArgumentException) {
        throw ResponseStatusException(HttpStatus.BAD_REQUEST, e.message)
      }
    } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
  }

  @Operation(summary = "List series' books", description = "Use POST /api/v1/books/list instead. Deprecated since 1.19.0.", tags = [OpenApiConfiguration.TagNames.SERIES, OpenApiConfiguration.TagNames.DEPRECATED])
  @Deprecated("use /v1/books/list instead")
  @PageableAsQueryParam
  @AuthorsAsQueryParam
  @GetMapping("v1/series/{seriesId}/books")
  fun getBooksBySeriesId(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") seriesId: String,
    @RequestParam(name = "media_status", required = false) mediaStatus: List<Media.Status>? = null,
    @RequestParam(name = "read_status", required = false) readStatus: List<ReadStatus>? = null,
    @RequestParam(name = "tag", required = false) tags: List<String>? = null,
    @RequestParam(name = "deleted", required = false) deleted: Boolean? = null,
    @RequestParam(name = "unpaged", required = false) unpaged: Boolean = false,
    @Parameter(hidden = true) @Authors authors: List<Author>? = null,
    @Parameter(hidden = true) page: Pageable,
  ): Page<BookDto> {
    principal.user.checkContentRestriction(seriesId)

    val sort =
      if (page.sort.isSorted)
        page.sort
      else
        Sort.by(Sort.Order.asc("metadata.numberSort"))

    val pageRequest =
      if (unpaged)
        UnpagedSorted(sort)
      else
        PageRequest.of(
          page.pageNumber,
          page.pageSize,
          sort,
        )

    val search =
      BookSearch(
        SearchCondition.AllOfBook(
          buildList {
            add(SearchCondition.SeriesId(SearchOperator.Is(seriesId)))
            if (!mediaStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(mediaStatus.map { SearchCondition.MediaStatus(SearchOperator.Is(it)) }))
            if (!readStatus.isNullOrEmpty()) add(SearchCondition.AnyOfBook(readStatus.map { SearchCondition.ReadStatus(SearchOperator.Is(it)) }))
            if (!tags.isNullOrEmpty()) add(SearchCondition.AnyOfBook(tags.map { SearchCondition.Tag(SearchOperator.Is(it)) }))
            if (!authors.isNullOrEmpty()) add(SearchCondition.AnyOfBook(authors.map { SearchCondition.Author(SearchOperator.Is(SearchCondition.AuthorMatch(it.name, it.role))) }))
            deleted?.let { add(SearchCondition.Deleted(if (it) SearchOperator.IsTrue else SearchOperator.IsFalse)) }
          },
        ),
      )
    return bookDtoRepository
      .findAll(
        search,
        SearchContext(principal.user),
        pageRequest,
      ).map { it.restrictUrl(!principal.user.isAdmin) }
  }

  @Operation(summary = "List series' collections", tags = [OpenApiConfiguration.TagNames.SERIES])
  @GetMapping("v1/series/{seriesId}/collections")
  fun getCollectionsBySeriesId(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable(name = "seriesId") seriesId: String,
  ): List<CollectionDto> {
    principal.user.checkContentRestriction(seriesId)

    return collectionRepository
      .findAllContainingSeriesId(seriesId, principal.user.getAuthorizedLibraryIds(null), principal.user.restrictions)
      .map { it.toDto() }
  }

  @Operation(summary = "Analyze series", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PostMapping("v1/series/{seriesId}/analyze")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun seriesAnalyze(
    @PathVariable seriesId: String,
  ) {
    taskEmitter.analyzeBook(bookRepository.findAllBySeriesId(seriesId), HIGH_PRIORITY)
  }

  @Operation(summary = "Refresh series metadata", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PostMapping("v1/series/{seriesId}/metadata/refresh")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun seriesRefreshMetadata(
    @PathVariable seriesId: String,
  ) {
    val books = bookRepository.findAllBySeriesId(seriesId)
    taskEmitter.refreshBookMetadata(books, priority = HIGH_PRIORITY)
    taskEmitter.refreshBookLocalArtwork(books, priority = HIGH_PRIORITY)
    taskEmitter.refreshSeriesLocalArtwork(seriesId, priority = HIGH_PRIORITY)
  }

  @Operation(summary = "Update series metadata", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PatchMapping("v1/series/{seriesId}/metadata")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateSeriesMetadata(
    @PathVariable seriesId: String,
    @Parameter(description = "Metadata fields to update. Set a field to null to unset the metadata. You can omit fields you don't want to update.")
    @Valid
    @RequestBody
    newMetadata: SeriesMetadataUpdateDto,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) = seriesMetadataRepository.findByIdOrNull(seriesId)?.let { existing ->
    val updated =
      with(newMetadata) {
        existing.copy(
          status = status ?: existing.status,
          statusLock = statusLock ?: existing.statusLock,
          title = title ?: existing.title,
          titleLock = titleLock ?: existing.titleLock,
          titleSort = titleSort ?: existing.titleSort,
          titleSortLock = titleSortLock ?: existing.titleSortLock,
          summary = summary ?: existing.summary,
          summaryLock = summaryLock ?: existing.summaryLock,
          language = language ?: existing.language,
          languageLock = languageLock ?: existing.languageLock,
          readingDirection = if (isSet("readingDirection")) readingDirection else existing.readingDirection,
          readingDirectionLock = readingDirectionLock ?: existing.readingDirectionLock,
          publisher = publisher ?: existing.publisher,
          publisherLock = publisherLock ?: existing.publisherLock,
          ageRating = if (isSet("ageRating")) ageRating else existing.ageRating,
          ageRatingLock = ageRatingLock ?: existing.ageRatingLock,
          genres =
            if (isSet("genres")) {
              if (genres != null) genres!! else emptySet()
            } else {
              existing.genres
            },
          genresLock = genresLock ?: existing.genresLock,
          tags =
            if (isSet("tags")) {
              if (tags != null) tags!! else emptySet()
            } else {
              existing.tags
            },
          tagsLock = tagsLock ?: existing.tagsLock,
          totalBookCount = if (isSet("totalBookCount")) totalBookCount else existing.totalBookCount,
          totalBookCountLock = totalBookCountLock ?: existing.totalBookCountLock,
          sharingLabels =
            if (isSet("sharingLabels")) {
              if (sharingLabels != null) sharingLabels!! else emptySet()
            } else {
              existing.sharingLabels
            },
          sharingLabelsLock = sharingLabelsLock ?: existing.sharingLabelsLock,
          links =
            if (isSet("links")) {
              if (links != null) links!!.map { WebLink(it.label!!, URI(it.url!!)) } else emptyList()
            } else {
              existing.links
            },
          linksLock = linksLock ?: existing.linksLock,
          alternateTitles =
            if (isSet("alternateTitles")) {
              if (alternateTitles != null) alternateTitles!!.map { AlternateTitle(it.label!!, it.title!!) } else emptyList()
            } else {
              existing.alternateTitles
            },
          alternateTitlesLock = alternateTitlesLock ?: existing.alternateTitlesLock,
        )
      }
    seriesMetadataRepository.update(updated)

    seriesRepository.findByIdOrNull(seriesId)?.let { eventPublisher.publishEvent(DomainEvent.SeriesUpdated(it)) }
  } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)

  @Operation(summary = "Mark series as read", description = "Mark all book for series as read", tags = [OpenApiConfiguration.TagNames.SERIES])
  @PostMapping("v1/series/{seriesId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun markSeriesAsRead(
    @PathVariable seriesId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    principal.user.checkContentRestriction(seriesId)

    seriesLifecycle.markReadProgressCompleted(seriesId, principal.user)
  }

  @Operation(summary = "Mark series as unread", description = "Mark all book for series as unread", tags = [OpenApiConfiguration.TagNames.SERIES])
  @DeleteMapping("v1/series/{seriesId}/read-progress")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun markSeriesAsUnread(
    @PathVariable seriesId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    principal.user.checkContentRestriction(seriesId)

    seriesLifecycle.deleteReadProgress(seriesId, principal.user)
  }

  @Operation(summary = "Get series read progress (Mihon)", description = "Mihon specific, due to how read progress is handled in Mihon.", tags = [OpenApiConfiguration.TagNames.MIHON])
  @GetMapping("v2/series/{seriesId}/read-progress/tachiyomi")
  fun getMihonReadProgressBySeriesId(
    @PathVariable seriesId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ): TachiyomiReadProgressV2Dto {
    principal.user.checkContentRestriction(seriesId)

    return readProgressDtoRepository.findProgressV2BySeries(seriesId, principal.user.id)
  }

  @Operation(summary = "Update series read progress (Mihon)", description = "Mihon specific, due to how read progress is handled in Mihon.", tags = [OpenApiConfiguration.TagNames.MIHON])
  @PutMapping("v2/series/{seriesId}/read-progress/tachiyomi")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  fun updateMihonReadProgressBySeriesId(
    @PathVariable seriesId: String,
    @RequestBody readProgress: TachiyomiReadProgressUpdateV2Dto,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    principal.user.checkContentRestriction(seriesId)

    bookDtoRepository
      .findAll(
        BookSearch(SearchCondition.SeriesId(SearchOperator.Is(seriesId))),
        SearchContext(principal.user),
        UnpagedSorted(Sort.by(Sort.Order.asc("metadata.numberSort"))),
      ).toList()
      .filter { book -> book.metadata.numberSort <= readProgress.lastBookNumberSortRead }
      .forEach { book ->
        if (book.readProgress?.completed != true)
          bookLifecycle.markReadProgressCompleted(book.id, principal.user)
      }
  }

  @Operation(summary = "Download series", description = "Download the whole series as a ZIP file.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @GetMapping("v1/series/{seriesId}/file", produces = [MediaType.APPLICATION_OCTET_STREAM_VALUE])
  @PreAuthorize("hasRole('FILE_DOWNLOAD')")
  fun downloadSeriesAsZip(
    @AuthenticationPrincipal principal: KomgaPrincipal,
    @PathVariable seriesId: String,
  ): ResponseEntity<StreamingResponseBody> {
    principal.user.checkContentRestriction(seriesId)

    val books = bookRepository.findAllBySeriesId(seriesId)

    val streamingResponse =
      StreamingResponseBody { responseStream: OutputStream ->
        ZipArchiveOutputStream(responseStream).use { zipStream ->
          zipStream.setMethod(ZipArchiveOutputStream.DEFLATED)
          zipStream.setLevel(Deflater.NO_COMPRESSION)
          zipStream.setUseZip64(Zip64Mode.Always)
          books.forEach { book ->
            val file = FileSystemResource(book.path)
            if (!file.exists()) {
              logger.warn { "Book file not found, skipping archive entry: ${file.path}" }
              return@forEach
            }

            logger.debug { "Adding file to zip archive: ${file.path}" }
            file.inputStream.use {
              zipStream.putArchiveEntry(ZipArchiveEntry(file.filename))
              IOUtils.copyLarge(it, zipStream, ByteArray(8192))
              zipStream.closeArchiveEntry()
            }
          }
        }
      }

    return ResponseEntity
      .ok()
      .headers(
        HttpHeaders().apply {
          contentDisposition =
            ContentDisposition
              .builder("attachment")
              .filename(seriesMetadataRepository.findById(seriesId).title + ".zip", UTF_8)
              .build()
        },
      ).contentType(MediaType.parseMediaType(ZIP.type))
      .body(streamingResponse)
  }

  @Operation(summary = "Delete series files", description = "Delete all of the series' books files on disk.", tags = [OpenApiConfiguration.TagNames.SERIES])
  @DeleteMapping("v1/series/{seriesId}/file")
  @PreAuthorize("hasRole('ADMIN')")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun deleteSeriesFile(
    @PathVariable seriesId: String,
  ) {
    taskEmitter.deleteSeries(
      seriesId = seriesId,
      priority = HIGHEST_PRIORITY,
    )
  }

  /**
   * Convenience function to check for content restriction.
   * This will retrieve data from repositories if needed.
   *
   * @throws[ResponseStatusException] if the user cannot access the content
   */
  private fun KomgaUser.checkContentRestriction(seriesId: String) {
    if (!canAccessAllLibraries()) {
      seriesRepository.getLibraryId(seriesId)?.let {
        if (!canAccessLibrary(it)) throw ResponseStatusException(HttpStatus.FORBIDDEN)
      } ?: throw ResponseStatusException(HttpStatus.NOT_FOUND)
    }
    if (restrictions.isRestricted)
      seriesMetadataRepository.findById(seriesId).let {
        if (!isContentAllowed(it.ageRating, it.sharingLabels)) throw ResponseStatusException(HttpStatus.FORBIDDEN)
      }
  }

  @PostMapping("v1/series/{seriesId}/push-to-kindle")
  @ResponseStatus(HttpStatus.ACCEPTED)
  fun pushToKindle(
    @PathVariable seriesId: String,
    @AuthenticationPrincipal principal: KomgaPrincipal,
  ) {
    principal.user.checkContentRestriction(seriesId)

    val books = bookRepository.findAllBySeriesId(seriesId)

    val bookPaths = books.map { it.url.path }

    if (bookPaths.isEmpty()) {
      throw ResponseStatusException(HttpStatus.NOT_FOUND, "No books in series")
    }

    try {
      val command = mutableListOf("python3", "/app/komga_custom/push_to_kindle.py")
      command.addAll(bookPaths)
      val processBuilder = ProcessBuilder(command)
      processBuilder.redirectErrorStream(true)
      val process = processBuilder.start()
      val reader = process.inputStream.bufferedReader()
      val output = reader.readText()
      logger.info { "Push to kindle script output: $output" }
      process.waitFor()
    } catch (e: Exception) {
      logger.error(e) { "Error while executing push to kindle script for series: $seriesId" }
      throw ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error while executing push to kindle script")
    }
  }
}

```
#### File: komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/KindleLogController.kt (NEW)
- **Purpose**: Handle Kindle log-related API endpoints
- **Requirements**:
  - GET endpoint to retrieve logs by job ID
  - GET endpoint to list all recent jobs
  - DELETE endpoint to clear logs
  - Proper error handling and response formatting
  - Admin-only access restriction
  - Log storage management (cleanup old logs)

## Data Structures

### Frontend Types

```typescript
// komga-webui/src/types/kindle-log.ts
interface KindleLogEntry {
  timestamp: string;
  level: 'INFO' | 'ERROR' | 'DEBUG' | 'WARNING';
  message: string;
  jobId: string;
}

interface KindleJob {
  id: string;
  type: 'BOOK' | 'SERIES';
  targetId: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  startTime: string;
  endTime?: string;
  logEntries: KindleLogEntry[];
}

interface KindleLogResponse {
  jobs: KindleJob[];
  totalElements: number;
}
```

### Backend DTOs

```kotlin
// komga/src/main/kotlin/org/gotson/komga/interfaces/api/rest/dto/KindleLogDto.kt
data class KindleLogEntryDto(
  val timestamp: Instant,
  val level: LogLevel,
  val message: String,
  val jobId: String
)

data class KindleJobDto(
  val id: String,
  val type: JobType,
  val targetId: String,
  val status: JobStatus,
  val startTime: Instant,
  val endTime: Instant?,
  val logEntries: List<KindleLogEntryDto>
)

data class KindleLogResponseDto(
  val jobs: List<KindleJobDto>,
  val totalElements: Int
)

enum class LogLevel {
  INFO, ERROR, DEBUG, WARNING
}

enum class JobType {
  BOOK, SERIES
}

enum class JobStatus {
  RUNNING, COMPLETED, FAILED
}
```

## Expected Output

### 1. Modified Sidebar Navigation
- History menu group with two sub-items:
  - "Scan History" (renamed from original History)
  - "Push To Kindle Progress" (new)

### 2. Push To Kindle Progress Page UI
- Page title: "Push To Kindle Progress"
- Auto-refreshing log display with:
  - Monospace font for log text
  - Color-coded log levels (INFO=blue, ERROR=red, DEBUG=gray, WARNING=orange)
  - Timestamps for each entry
  - Scrollable container for long logs
- Action buttons:
  - Refresh (manual refresh)
  - Clear Logs (with confirmation dialog)
- Loading indicator during API calls
- Error message display when API calls fail

### 3. Backend API Endpoints
- `GET /api/v1/kindle-logs` - Retrieve all recent Kindle jobs with logs
- `GET /api/v1/kindle-logs/{jobId}` - Retrieve specific job logs
- `DELETE /api/v1/kindle-logs` - Clear all logs
- `POST /api/v1/books/{bookId}/push-to-kindle` - Modified to return job ID
- `POST /api/v1/series/{seriesId}/push-to-kindle` - Modified to return job ID

### 4. Log Capture and Storage
- Real-time log capture from push_to_kindle.py script execution
- Temporary storage of logs with automatic cleanup
- Unique job identification for tracking multiple operations
- Proper error handling and log level classification

### 5. User Experience
- Seamless navigation between Scan History and Push To Kindle Progress
- Real-time log updates without page refresh
- Clear visual indication of operation status
- Responsive design that works on all screen sizes
- Consistent with existing Komga UI patterns