import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Space, message, Upload, Row, Col, Divider, Card, Popconfirm } from 'antd'
import { EditOutlined, DeleteOutlined, ReloadOutlined, FolderOutlined, FileTextOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import apiClient from '../api/client'

// 数据库存的就是 BP 数值本身（用户填 25 BP 即存 25）
const fmtBP = (v: number | undefined | null): string => {
  if (v === undefined || v === null || v === 0) return ''
  return Number(v).toFixed(0) + ' BP'
}

interface TreeNode {
  key: string
  id?: number
  coa_cd: string
  coa_name: string | null
  value?: number | null
  has_data: boolean
  preview_values?: number[]
  last_update?: string
  remark?: string
  children?: TreeNode[]
}

const ParamCustomStrategyPage = () => {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentCoa, setCurrentCoa] = useState<TreeNode | null>(null)
  const [form] = Form.useForm()

  const fetchTree = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get('/param/custom-strategy/tree')
      const convert = (nodes: any[]): TreeNode[] =>
        nodes.map(n => {
          // 判断是否有任何非零策略值
          const vals = n.preview_values || []
          const has_any_value = vals.some((v: number | null) => v !== null && v !== undefined && v !== 0)
          return {
            key: `coa_${n.id}`,
            id: n.id,
            coa_cd: n.coa_cd,
            coa_name: n.coa_name,
            value: n.value,
            has_data: !!n.value,
            has_any_value,
            preview_values: n.preview_values,
            last_update: n.last_update,
            remark: n.remark,
            children: n.children ? convert(n.children) : []
          }
        })
      setTree(convert(res.data || []))
    } catch (e: any) {
      message.error('加载账户册树失败：' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTree()
  }, [])

  // 打开编辑 Modal：加载该账户册的 24 期策略值
  const openEdit = async (record: TreeNode) => {
    setCurrentCoa(record)
    const values: any = {
      coa_cd: record.coa_cd,
      coa_name: record.coa_name,
      remark: record.remark || ''
    }
    // 24 期默认值
    const vals = record.preview_values || new Array(24).fill(0)
    for (let i = 1; i <= 24; i++) {
      values[`strategy_M${i}`] = vals[i - 1] || 0
    }
    form.setFieldsValue(values)
    setModalOpen(true)
  }

  // 保存策略
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const res = await apiClient.post('/param/custom-strategy/save', values)
      if (res.data?.success !== false) {
        message.success(res.data?.message || '保存成功')
        setModalOpen(false)
        fetchTree()
      } else {
        message.error(res.data?.message || '保存失败')
      }
    } catch (e: any) {
      if (e.errorFields) return
      message.error('保存失败：' + (e.response?.data?.detail || e.message))
    }
  }

  // 删除策略
  const handleDelete = async (coa_cd: string) => {
    try {
      await apiClient.delete(`/param/custom-strategy/${encodeURIComponent(coa_cd)}`)
      message.success('删除成功')
      fetchTree()
    } catch (e: any) {
      message.error('删除失败：' + (e.response?.data?.detail || e.message))
    }
  }

  const handleExport = () => {
    window.open(apiClient.defaults.baseURL + '/param/custom-strategy/export', '_blank')
  }

  const handleImport = async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await apiClient.post('/param/custom-strategy/import', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success(`导入成功: 新增 ${res.data.inserted} 条, 更新 ${res.data.updated} 条`)
      fetchTree()
    } catch (e: any) {
      message.error('导入失败：' + (e.response?.data?.detail || e.message))
    }
    return false
  }

  // ===== 24 列主表 =====
  const buildColumns = () => {
    const cols: any[] = [
      {
        title: '账户册编码', dataIndex: 'coa_cd', key: 'coa_cd',
        width: 200, fixed: 'left' as const, ellipsis: true,
        render: (val: string) => <span style={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{val}</span>
      },
      {
        title: '账户册名称', dataIndex: 'coa_name', key: 'coa_name',
        width: 260, fixed: 'left' as const, ellipsis: true,
        render: (val: string, record: TreeNode) => (
          <Space>
            {record.has_any_value
              ? <FileTextOutlined style={{ color: '#722ed1' }} />
              : <FolderOutlined style={{ color: '#999' }} />}
            <span style={{ color: record.has_any_value ? 'inherit' : '#999', whiteSpace: 'nowrap' }}>{val || '-'}</span>
            {!record.has_any_value && record.has_data && (
              <span style={{ color: '#999', fontSize: 11, padding: '0 4px', background: '#f5f5f5', border: '1px solid #d9d9d9', borderRadius: 2 }}>未设置</span>
            )}
          </Space>
        )
      }
    ]
    for (let i = 1; i <= 24; i++) {
      cols.push({
        title: `M${i}`,
        key: `m_${i}`,
        width: 78,
        align: 'right' as const,
        render: (_: any, record: TreeNode) => {
          const vals = record.preview_values || []
          const v = vals[i - 1]
          if (!record.has_data || v === undefined || v === null || v === 0) {
            return <span style={{ color: '#bbb' }}>-</span>
          }
          const color = v > 0 ? '#cf1322' : '#52c41a'
          return <span style={{ color, fontWeight: 'bold' }}>{fmtBP(v)}</span>
        }
      })
    }
    cols.push({
      title: '操作', key: 'action', width: 160, fixed: 'right' as const,
      render: (_: any, record: TreeNode) => (
        <Space>
          {record.has_data ? (
            <>
              <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
                编辑
              </Button>
              <Popconfirm title="确认删除该账户册的策略?" onConfirm={() => handleDelete(record.coa_cd)}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </>
          ) : (
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
              新增
            </Button>
          )}
        </Space>
      )
    })
    return cols
  }

  return (
    <div>
      <h2>参数配置 / 定价策略</h2>
      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Button icon={<ReloadOutlined />} onClick={fetchTree}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出Excel</Button>
          <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={handleImport}>
            <Button icon={<UploadOutlined />}>导入Excel</Button>
          </Upload>
          <span style={{ color: '#666' }}>
            每个账户册对应一组 24 个月策略值。
            <span style={{ color: '#cf1322' }}>红</span>表示加点，<span style={{ color: '#52c41a' }}>绿</span>表示减点。
          </span>
        </Space>

        <Table
          columns={buildColumns()}
          dataSource={tree}
          rowKey="key"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 3260, y: 600 }}
          bordered
          defaultExpandAllRows
        />
      </Card>

      <Modal
        title={currentCoa ? `定价策略 - ${currentCoa.coa_cd} ${currentCoa.coa_name}` : '定价策略'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
        width={1100}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="coa_cd" label="账户册编码">
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="coa_name" label="账户册名称">
                <Input disabled style={{ color: '#999' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" style={{ color: '#722ed1', fontWeight: 'bold' }}>
            未来 24 个月策略值（单位：BP，1 BP = 0.01%）
          </Divider>

          <div style={{ color: '#999', marginBottom: 12, fontSize: 12 }}>
            录入 BP 值，保存后即为该账户册的策略值。如需 +25BP 加点，请填 <b>25</b>。
          </div>
          <Row gutter={[12, 8]}>
            {Array.from({ length: 24 }, (_, i) => i + 1).map(i => (
              <Col span={4} key={`m_${i}`}>
                <Form.Item
                  name={`strategy_M${i}`}
                  label={`M${i}`}
                  style={{ marginBottom: 8 }}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    step={5}
                    placeholder="0"
                    addonAfter="BP"
                  />
                </Form.Item>
              </Col>
            ))}
          </Row>

          <Form.Item name="remark" label="备注" style={{ marginTop: 12 }}>
            <Input.TextArea rows={2} placeholder="策略说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ParamCustomStrategyPage