import { useState, useEffect } from 'react'
import {
  Card, Button, Steps, Progress, Space, message, DatePicker, Table, Statistic,
  Row, Col, Divider, Popconfirm, Modal, Input, Tag, Tooltip, Empty
} from 'antd'
import {
  PlayCircleOutlined, CheckCircleOutlined, ReloadOutlined, TrophyOutlined,
  DollarOutlined, DeleteOutlined, PlusOutlined, EyeOutlined, FileTextOutlined
} from '@ant-design/icons'
import dayjs from 'dayjs'
import apiClient from '../api/client'

interface VersionInfo {
  calc_version: string
  task_id: string
  data_date: string
  status: string
  progress: number
  started_at: string
  completed_at: string
  created_at: string
  error_message?: string
  index_count: number
  plan_count: number
}

const CalculatePage = () => {
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [dataDate, setDataDate] = useState<string>(dayjs().format('YYYY-MM-DD'))
  const [result, setResult] = useState<any>(null)
  const [currentVersion, setCurrentVersion] = useState<string>('')
  const [versions, setVersions] = useState<VersionInfo[]>([])

  // 创建空版本
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createDate, setCreateDate] = useState<string>(dayjs().format('YYYY-MM-DD'))
  const [createRemark, setCreateRemark] = useState<string>('')
  const [creating, setCreating] = useState(false)

  // 详情弹窗
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [detailVersion, setDetailVersion] = useState<VersionInfo | null>(null)

  const fetchVersions = async () => {
    try {
      const res = await apiClient.get('/calculate/versions', { params: { limit: 50, include_empty: true } })
      setVersions(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      console.error('加载版本列表失败', e)
    }
  }

  useEffect(() => {
    fetchVersions()
  }, [])

  const handleCalculate = async () => {
    setLoading(true)
    setCurrentStep(0)
    setProgress(0)
    setResult(null)
    setCurrentVersion('')

    try {
      setCurrentStep(1)
      setProgress(20)
      await new Promise(r => setTimeout(r, 200))

      setCurrentStep(2)
      setProgress(40)
      await new Promise(r => setTimeout(r, 200))

      setCurrentStep(3)
      setProgress(70)
      const res = await apiClient.post('/calculate/start', { data_date: dataDate })

      setCurrentStep(4)
      setProgress(90)
      setCurrentVersion(res.data.calc_version || '')

      const simRes = await apiClient.post('/calculate/simulate')
      setResult(simRes.data)

      setProgress(100)
      setCurrentStep(5)
      message.success(`计算完成! 版本: ${res.data.calc_version}`)
      fetchVersions()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '计算失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateEmptyVersion = async () => {
    setCreating(true)
    try {
      const res = await apiClient.post('/calculate/versions', {
        data_date: createDate,
        remark: createRemark
      })
      message.success(`空版本创建成功: ${res.data.calc_version}`)
      setCreateModalOpen(false)
      setCreateRemark('')
      fetchVersions()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteVersion = async (version: string) => {
    try {
      const res = await apiClient.delete(`/calculate/versions/${version}`)
      const { deleted_task, deleted_index, deleted_plan } = res.data
      message.success(
        `版本 ${version} 已删除（任务${deleted_task}条 + 指标${deleted_index}条 + 计划${deleted_plan}条）`
      )
      fetchVersions()
      // 如果删除的是当前查看的版本，清空结果
      if (version === currentVersion) {
        setResult(null)
        setCurrentVersion('')
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '删除失败')
    }
  }

  const showVersionDetail = async (v: VersionInfo) => {
    setDetailVersion(v)
    setDetailModalOpen(true)
  }

  const steps = [
    { title: '准备' },
    { title: '加载参数' },
    { title: '加载数据' },
    { title: '计算执行' },
    { title: '结果提取' },
    { title: '完成' }
  ]

  const versionColumns = [
    {
      title: '计算版本', dataIndex: 'calc_version', key: 'calc_version', width: 140,
      render: (v: string) => <Tag color="blue" style={{ fontFamily: 'monospace' }}>{v}</Tag>
    },
    { title: '任务ID', dataIndex: 'task_id', key: 'task_id', width: 220, ellipsis: true },
    {
      title: '数据日期', dataIndex: 'data_date', key: 'data_date', width: 110,
      render: (d: string) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 90,
      render: (s: string) => {
        const colorMap: Record<string, string> = {
          success: 'green', failed: 'red', running: 'blue', pending: 'default', empty: 'orange',
        }
        const labelMap: Record<string, string> = {
          success: '已完成', failed: '失败', running: '执行中', pending: '待执行', empty: '空版本',
        }
        return <Tag color={colorMap[s] || 'default'}>{labelMap[s] || s}</Tag>
      }
    },
    {
      title: '指标/计划', key: 'counts', width: 110,
      render: (_: any, r: VersionInfo) => (
        <span style={{ fontSize: 12, color: '#666' }}>
          {r.index_count} / {r.plan_count}
        </span>
      )
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作', key: 'action', width: 180, fixed: 'right' as const,
      render: (_: any, r: VersionInfo) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button size="small" icon={<EyeOutlined />} onClick={() => showVersionDetail(r)} />
          </Tooltip>
          <Popconfirm
            title="确定清除该版本的所有结果吗？"
            description={
              <div>
                <div>版本：<b>{r.calc_version}</b></div>
                <div style={{ marginTop: 4, color: '#999', fontSize: 12 }}>
                  将删除 {r.index_count + r.plan_count} 条结果数据，且不可恢复！
                </div>
              </div>
            }
            okText="确认清除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDeleteVersion(r.calc_version)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>清除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ]

  return (
    <div>
      <h2>计算执行</h2>

      <Card
        title={<><PlayCircleOutlined /> 执行计算</>}
        extra={
          <Space>
            <Button icon={<PlusOutlined />} onClick={() => {
              setCreateDate(dataDate)
              setCreateModalOpen(true)
            }}>
              创建空版本
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <span style={{ marginRight: 16 }}>数据日期:</span>
            <DatePicker
              value={dayjs(dataDate)}
              onChange={(date) => setDataDate(date?.format('YYYY-MM-DD') || '')}
              disabled={loading}
            />
            <span style={{ marginLeft: 16, color: '#666' }}>
              新版本将自动分配版本号（YYYYMMDD-XXXX）
            </span>
          </div>

          <Steps current={currentStep} items={steps} />

          {progress > 0 && (
            <Progress percent={progress} status={progress === 100 ? 'success' : 'active'} />
          )}

          <Space>
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleCalculate}
              loading={loading}
            >
              {progress === 100 && result ? '重新计算' : '开始计算'}
            </Button>
            {currentVersion && (
              <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                当前版本: {currentVersion}
              </Tag>
            )}
          </Space>
        </Space>
      </Card>

      {result && (
        <Card
          title={<><TrophyOutlined /> 计算结果（{currentVersion}）</>}
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="总资产"
                value={(result.indicators.total_assets || 0) / 1e8}
                precision={2} suffix="亿"
                valueStyle={{ color: '#3f8600' }}
                prefix={<DollarOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="总负债"
                value={Math.abs(result.indicators.total_liabilities || 0) / 1e8}
                precision={2} suffix="亿"
                valueStyle={{ color: '#cf1322' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="净资产"
                value={(result.indicators.net_position || 0) / 1e8}
                precision={2} suffix="亿"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="平均利率"
                value={(result.indicators.avg_rate || 0) * 100}
                precision={2} suffix="%"
              />
            </Col>
          </Row>

          <Divider />

          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="FTP总收入" value={(result.strategy.ftp_total || 0) / 1e8} precision={2} suffix="亿" />
            </Col>
            <Col span={6}>
              <Statistic title="净息差(NII)" value={(result.strategy.nii || 0) / 1e8} precision={2} suffix="亿" />
            </Col>
            <Col span={6}>
              <Statistic title="净息差率(NIM)" value={(result.strategy.nim || 0) * 100} precision={2} suffix="%" />
            </Col>
            <Col span={6}>
              <Statistic title="VaR(99%)" value={(result.strategy.var_99 || 0) / 1e8} precision={2} suffix="亿" valueStyle={{ color: '#faad14' }} />
            </Col>
          </Row>
        </Card>
      )}

      <Card
        title={<><FileTextOutlined /> 计算版本管理</>}
        extra={
          <Space>
            <span style={{ color: '#999', fontSize: 12 }}>
              共 {versions.length} 个版本
            </span>
            <Button icon={<ReloadOutlined />} onClick={fetchVersions}>刷新</Button>
          </Space>
        }
      >
        {versions.length === 0 ? (
          <Empty description="暂无计算版本，请先执行计算或创建空版本" />
        ) : (
          <Table
            columns={versionColumns}
            dataSource={versions}
            rowKey="task_id"
            size="small"
            pagination={{ pageSize: 20, showSizeChanger: true }}
            scroll={{ x: 1000 }}
          />
        )}
      </Card>

      {/* 创建空版本弹窗 */}
      <Modal
        title={<><PlusOutlined /> 创建空版本</>}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={handleCreateEmptyVersion}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <div style={{ marginBottom: 4 }}>数据日期：</div>
            <DatePicker
              value={dayjs(createDate)}
              onChange={(d) => setCreateDate(d?.format('YYYY-MM-DD') || '')}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <div style={{ marginBottom: 4 }}>备注（可选）：</div>
            <Input.TextArea
              value={createRemark}
              onChange={(e) => setCreateRemark(e.target.value)}
              rows={3}
              placeholder="例如：预留版本用于手工导入数据"
            />
          </div>
          <div style={{ background: '#f0f5ff', padding: 12, borderRadius: 4, fontSize: 12, color: '#666' }}>
            创建后将分配版本号 <b style={{ color: '#1890ff' }}>{createDate.replace(/-/g, '')}-XXXX</b>
            （同日已有版本自动递增序列码）。版本创建后可继续执行计算或导入数据。
          </div>
        </Space>
      </Modal>

      {/* 版本详情弹窗 */}
      <Modal
        title={<><EyeOutlined /> 版本详情</>}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={<Button onClick={() => setDetailModalOpen(false)}>关闭</Button>}
        width={700}
      >
        {detailVersion && (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div><b>计算版本：</b><Tag color="blue">{detailVersion.calc_version}</Tag></div>
            <div><b>任务ID：</b><code>{detailVersion.task_id}</code></div>
            <div><b>数据日期：</b>{detailVersion.data_date ? new Date(detailVersion.data_date).toLocaleDateString('zh-CN') : '-'}</div>
            <div><b>状态：</b><Tag color={detailVersion.status === 'success' ? 'green' : 'orange'}>{detailVersion.status}</Tag></div>
            <div><b>进度：</b>{detailVersion.progress}%</div>
            <div><b>结果数据：</b>{detailVersion.index_count} 条指标 / {detailVersion.plan_count} 条计划</div>
            <div><b>创建时间：</b>{detailVersion.created_at ? new Date(detailVersion.created_at).toLocaleString('zh-CN') : '-'}</div>
            <div><b>开始时间：</b>{detailVersion.started_at ? new Date(detailVersion.started_at).toLocaleString('zh-CN') : '-'}</div>
            <div><b>完成时间：</b>{detailVersion.completed_at ? new Date(detailVersion.completed_at).toLocaleString('zh-CN') : '-'}</div>
            {detailVersion.error_message && (
              <div>
                <b>错误/备注：</b>
                <pre style={{
                  background: '#f5f5f5', padding: 8, borderRadius: 4,
                  maxHeight: 200, overflow: 'auto', fontSize: 12
                }}>
                  {detailVersion.error_message}
                </pre>
              </div>
            )}
          </Space>
        )}
      </Modal>
    </div>
  )
}

export default CalculatePage