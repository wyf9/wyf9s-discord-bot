import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: 'wyf9s-discord-bot',
  description: '多功能 Discord 机器人 · 文档',

  base: '/',

  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  // Internal notes for AI agents / maintainers — never shipped to the site.
  srcExclude: ['agents/**'],

  head: [
    ['meta', { name: 'theme-color', content: '#5865F2' }],
    ['link', { rel: 'icon', href: '/favicon.png' }],
    ['link', { rel: 'apple-touch-icon', href: '/favicon.png' }],
  ],

  themeConfig: {
    // Shared across locales
    logo: '/favicon.png',

    socialLinks: [
      { icon: 'github', link: 'https://github.com/wyf9/wyf9s-discord-bot' },
    ],

    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
              modal: {
                noResultsText: '无法找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: {
                  selectText: '选择',
                  navigateText: '切换',
                  closeText: '关闭',
                },
              },
            },
          },
          en: {
            translations: {
              button: { buttonText: 'Search', buttonAriaLabel: 'Search' },
              modal: {
                noResultsText: 'No results found',
                resetButtonTitle: 'Reset search',
                footer: {
                  selectText: 'to select',
                  navigateText: 'to navigate',
                  closeText: 'to close',
                },
              },
            },
          },
        },
      },
    },
  },

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'wyf9s-discord-bot',
      description: '多功能 Discord 机器人 · 文档',
      themeConfig: {
        nav: [
          { text: '指南', link: '/guide/introduction' },
          { text: '模块 & 指令', link: '/modules/' },
          { text: '配置', link: '/guide/configuration' },
          {
            text: '法律',
            items: [
              { text: '服务条款', link: '/legal/tos' },
              { text: '隐私政策', link: '/legal/privacy' },
            ],
          },
          {
            text: '相关链接',
            items: [
              { text: '添加 Bot', link: 'https://discord.com/oauth2/authorize?client_id=1268221966544932945' },
              { text: 'GitHub 仓库', link: 'https://github.com/wyf9/wyf9s-discord-bot' },
              { text: 'discord.py 文档', link: 'https://discordpy.readthedocs.io/' },
              { text: '联系开发者', link: 'https://wyf9.top/c' },
              { text: 'config.example.yaml', link: 'https://github.com/wyf9/wyf9s-discord-bot/blob/main/config.example.yaml' },
              { text: 'perm.example.yaml', link: 'https://github.com/wyf9/wyf9s-discord-bot/blob/main/perm.example.yaml' },
            ],
          },
        ],

        sidebar: {
          '/guide/': [
            {
              text: '开始',
              items: [
                { text: '项目介绍', link: '/guide/introduction' },
                { text: '快速开始', link: '/guide/getting-started' },
                { text: '配置说明', link: '/guide/configuration' },
                { text: '权限系统', link: '/guide/permissions' },
                { text: '限速与 Rate Limit', link: '/guide/rate-limit' },
              ],
            },
          ],
          '/modules/': [
            {
              text: '总览',
              items: [{ text: '模块总览', link: '/modules/' }],
            },
            {
              text: '指令模块',
              items: [
                { text: '工具 / 管理 (tools)', link: '/modules/tools' },
                { text: '表情 (emoji)', link: '/modules/emoji' },
                { text: '频道锁定 (lock)', link: '/modules/lock' },
                { text: '语音频道 (voice)', link: '/modules/voice' },
                { text: '管理指令 (admin)', link: '/modules/admin' },
                { text: '动态权限 (perm)', link: '/modules/perm' },
                { text: '公告推送 (announce)', link: '/modules/announce' },
                { text: '多语言 (lang)', link: '/modules/lang' },
              ],
            },
            {
              text: '事件 / 服务模块',
              items: [
                { text: '自动管理 (manage)', link: '/modules/manage' },
                { text: '反垃圾 (antispam)', link: '/modules/antispam' },
                { text: '审计日志 (audit)', link: '/modules/audit' },
              ],
            },
          ],
          '/legal/': [
            {
              text: '法律',
              items: [
                { text: '服务条款', link: '/legal/tos' },
                { text: '隐私政策', link: '/legal/privacy' },
              ],
            },
          ],
        },

        editLink: {
          pattern: 'https://github.com/wyf9/wyf9s-discord-bot/edit/main/docs/:path',
          text: '在 GitHub 上编辑此页',
        },

        docFooter: { prev: '上一页', next: '下一页' },
        outline: { label: '本页目录', level: [2, 3] },
        lastUpdated: {
          text: '最后更新于',
          formatOptions: { dateStyle: 'short', timeStyle: 'short' },
        },
        footer: {
          message: '基于 MIT 许可发布',
          copyright: 'Copyright © 2025 wyf9',
        },
        darkModeSwitchLabel: '外观',
        lightModeSwitchTitle: '切换到浅色模式',
        darkModeSwitchTitle: '切换到深色模式',
        sidebarMenuLabel: '菜单',
        returnToTopLabel: '返回顶部',
        langMenuLabel: '切换语言',
      },
    },

    en: {
      label: 'English',
      lang: 'en-US',
      title: 'wyf9s-discord-bot',
      description: 'Multi-purpose Discord bot · Docs',
      themeConfig: {
        nav: [
          { text: 'Guide', link: '/en/guide/introduction' },
          { text: 'Modules & Commands', link: '/en/modules/' },
          { text: 'Configuration', link: '/en/guide/configuration' },
          {
            text: 'Legal',
            items: [
              { text: 'Terms of Service', link: '/en/legal/tos' },
              { text: 'Privacy Policy', link: '/en/legal/privacy' },
            ],
          },
          {
            text: 'Links',
            items: [
              { text: 'Add the Bot', link: 'https://discord.com/oauth2/authorize?client_id=1268221966544932945' },
              { text: 'GitHub Repository', link: 'https://github.com/wyf9/wyf9s-discord-bot' },
              { text: 'discord.py Docs', link: 'https://discordpy.readthedocs.io/' },
              { text: 'Contact Developer', link: 'https://wyf9.top/c' },
              { text: 'config.example.yaml', link: 'https://github.com/wyf9/wyf9s-discord-bot/blob/main/config.example.yaml' },
              { text: 'perm.example.yaml', link: 'https://github.com/wyf9/wyf9s-discord-bot/blob/main/perm.example.yaml' },
            ],
          },
        ],

        sidebar: {
          '/en/guide/': [
            {
              text: 'Getting Started',
              items: [
                { text: 'Introduction', link: '/en/guide/introduction' },
                { text: 'Getting Started', link: '/en/guide/getting-started' },
                { text: 'Configuration', link: '/en/guide/configuration' },
                { text: 'Permission System', link: '/en/guide/permissions' },
                { text: 'Rate Limiting', link: '/en/guide/rate-limit' },
              ],
            },
          ],
          '/en/modules/': [
            {
              text: 'Overview',
              items: [{ text: 'Modules Overview', link: '/en/modules/' }],
            },
            {
              text: 'Command Modules',
              items: [
                { text: 'Tools / Admin (tools)', link: '/en/modules/tools' },
                { text: 'Emoji (emoji)', link: '/en/modules/emoji' },
                { text: 'Channel Lock (lock)', link: '/en/modules/lock' },
                { text: 'Voice Channel (voice)', link: '/en/modules/voice' },
                { text: 'Admin Commands (admin)', link: '/en/modules/admin' },
                { text: 'Dynamic Permissions (perm)', link: '/en/modules/perm' },
                { text: 'Announcement Following (announce)', link: '/en/modules/announce' },
                { text: 'Localization (lang)', link: '/en/modules/lang' },
              ],
            },
            {
              text: 'Event / Service Modules',
              items: [
                { text: 'Auto Management (manage)', link: '/en/modules/manage' },
                { text: 'Anti-Spam (antispam)', link: '/en/modules/antispam' },
                { text: 'Audit Log (audit)', link: '/en/modules/audit' },
              ],
            },
          ],
          '/en/legal/': [
            {
              text: 'Legal',
              items: [
                { text: 'Terms of Service', link: '/en/legal/tos' },
                { text: 'Privacy Policy', link: '/en/legal/privacy' },
              ],
            },
          ],
        },

        editLink: {
          pattern: 'https://github.com/wyf9/wyf9s-discord-bot/edit/main/docs/:path',
          text: 'Edit this page on GitHub',
        },

        docFooter: { prev: 'Previous', next: 'Next' },
        outline: { label: 'On this page', level: [2, 3] },
        lastUpdated: {
          text: 'Last updated',
          formatOptions: { dateStyle: 'short', timeStyle: 'short' },
        },
        footer: {
          message: 'Released under the MIT License',
          copyright: 'Copyright © 2025 wyf9',
        },
        darkModeSwitchLabel: 'Appearance',
        lightModeSwitchTitle: 'Switch to light theme',
        darkModeSwitchTitle: 'Switch to dark theme',
        sidebarMenuLabel: 'Menu',
        returnToTopLabel: 'Return to top',
        langMenuLabel: 'Change language',
      },
    },
  },
})
