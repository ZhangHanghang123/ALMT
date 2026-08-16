import ResultViewLayout from './ResultViewLayout'

const mHeaders = Array.from({ length: 24 }, (_, i) => `M${i + 1}`)

const ResultAllocationAveragePage = () => (
  <ResultViewLayout
    endpoint="/result-view/allocation-average"
    title="中间表-分摊日均"
    columns={24}
    columnHeaders={mHeaders}
    description="账户册 + M1~M24 规划日均，来自业务计划 plan_average_i。"
  />
)

export default ResultAllocationAveragePage