import { useEffect, useState } from 'react'
import { Select, Space, Tag, Tooltip } from 'antd'
import { ReloadOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

export interface VersionInfo {
  calc_version: string
  task_id: string
  data_date: string
  status: string
  progress: number
  started_at: string
  completed_at: string
  error_message?: string
  index_count: number
  plan_count: number
}

interface VersionSelectorProps {
  /** 选中的版本号（受控）；'' 或 undefined 表示"当前参数（不指定版本）" */
  value?: string
  onChange?: (v: string) => void
  /** 是否显示"当前参数"空选项（默认 true） */
  allowEmpty?: boolean
  /** 是否包含空版本（默认 true） */
  includeEmpty?: boolean
  /** 宽度（默认 280） */
  width?: number | string
  /** 占位文本 */
  placeholder?: string
  /** 显示左侧标签 "计算版本：" */
  showLabel?: boolean
  /** 显示右侧刷新按钮 */
  showRefresh?: boolean
  /** 自定义样式 */
  style?: React.CSSProperties
}

/**
 * 计算版本下拉选择器（共享组件）
 *
 * 数据源：GET /api/calculate/versions?include_empty={includeEmpty}
 *
 * 用法：
 *   <VersionSelector value={version} onChange={setVersion} />
 */
const VersionSelector: React.FC<VersionSelectorProps> = ({
  value,
  onChange,
  allowEmpty = true,
  includeEmpty = true,
  width = 280,
  placeholder = '请选择计算版本',
  showLabel = true,
  showRefresh = true,
  style,
}) => {
  const [versions, setVersions] = useState<VersionInfo[]>([])
  const [loading, setLoading] = useState(false)

  const fetchVersions = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/calculate/versions', {
        params: { limit: 100, include_empty: includeEmpty },
      })
      const data = Array.isArray(res.data) ? res.data : []
      setVersions(data)
    } catch (e) {
      console.error('加载版本列表失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVersions()
  }, [includeEmpty])

  // 状态标签渲染
  const statusTag = (s: string) => {
    const colorMap: Record<string, string> = {
      success: 'green', failed: 'red', running: 'blue',
      pending: 'default', empty: 'orange',
    }
    const labelMap: Record<string, string> = {
      success: '已完成', failed: '失败', running: '执行中',
      pending: '待执行', empty: '空版本',
    }
    return <Tag color={colorMap[s] || 'default'} style={{ marginLeft: 4 }}>{labelMap[s] || s}</Tag>
  }

  const options = [
    ...(allowEmpty ? [{
      value: '',
      label: (
        <Space>
          <ClockCircleOutlined style={{ color: '#999' }} />
          <span style={{ color: '#999' }}>当前参数（不指定版本）</span>
        </Space>
      ),
    }] : []),
    ...versions.map(v => ({
      value: v.calc_version || v.task_id,
      label: (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <span style={{ fontFamily: 'monospace' }}>{v.calc_version || '(无版本)'}</span>
          <span style={{ color: '#999', fontSize: 12 }}>
            {v.data_date ? new Date(v.data_date).toLocaleDateString('zh-CN') : ''}
          </span>
          {statusTag(v.status)}
          {v.index_count > 0 && (
            <span style={{ color: '#52c41a', fontSize: 12 }}>指标×{v.index_count}</span>
          )}
        </Space>
      ),
      data: v,
    })),
  ]

  return (
    <Space style={style}>
      {showLabel && <span style={{ color: '#666' }}>计算版本:</span>}
      <Tooltip title="选择计算结果版本（默认显示当前参数）">
        <Select
          value={value || ''}
          onChange={onChange}
          loading={loading}
          options={options}
          placeholder={placeholder}
          style={{ width, minWidth: 200 }}
          showSearch
          optionFilterProp="label"
          notFoundContent={loading ? '加载中...' : '暂无可用版本'}
        />
      </Tooltip>
      {showRefresh && (
        <Tooltip title="刷新版本列表">
          <ReloadOutlined
            onClick={fetchVersions}
            style={{ color: '#1890ff', cursor: 'pointer' }}
          />
        </Tooltip>
      )}
    </Space>
  )
}

export default VersionSelector